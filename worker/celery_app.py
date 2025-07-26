"""
worker/celery_app.py
====================

Central Celery app for DevOps-AI.  Features
------------------------------------------
* Secure Azure-Redis URLs (adds ssl_cert_reqs).
* Strong default limits + retry/broker tuning.
* Multiple queues (github_api, repo_operations, deployments, maintenance).
* OpenTelemetry (Celery + HTTP) with Azure Monitor exporter.
* Health-check tasks and GitHub connectivity test.
* Task-lifecycle signal logging.
* Single `app` instance (no duplicates).
"""

from __future__ import annotations

import logging
from typing import Dict

from celery import Celery, signals
from gateway.config import settings
from gateway.core.logging import setup_logging, get_logger

# ───────────────────────────── Logging bootstrap ──────────────────────────
setup_logging(debug=settings.debug)
logger = get_logger(__name__)

# ───────────────────────────── Helpers ────────────────────────────────────
class RedisUrlBuilder:
    """Add ssl_cert_reqs=none to rediss:// URLs (dev convenience)."""

    @staticmethod
    def build_secure(url: str) -> str:
        if not url.startswith("rediss://"):
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}ssl_cert_reqs=none"


# ───────────────────────────── Factory ────────────────────────────────────
class CeleryAppFactory:
    """Create a fully configured Celery application."""

    @staticmethod
    def create_app(name: str = "devops-agent") -> Celery:
        broker = RedisUrlBuilder.build_secure(settings.celery_broker_url)
        backend = RedisUrlBuilder.build_secure(settings.celery_result_backend)

        logger.info("Using broker URL: %s", broker.replace(broker.split("@")[0], "***"))
        logger.info("Using backend URL: %s", backend.replace(backend.split("@")[0], "***"))

        app = Celery(
            name,
            broker=broker,
            backend=backend,
            include=[
                "worker.tasks.github_tasks",  # your task module
            ],
        )

        CeleryAppFactory._configure(app)
        CeleryAppFactory._setup_task_routes(app)
        CeleryAppFactory._setup_otel(app)
        return app

    # ---------------------------------------------------------------------
    @staticmethod
    def _configure(app: Celery) -> None:
        app.conf.update(
            # Serialization
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            # Timing
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=1800,
            task_soft_time_limit=1500,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
            result_expires=3600,
            # Redis / broker
            broker_connection_retry_on_startup=True,
            broker_pool_limit=10,
            broker_connection_max_retries=10,
            redis_socket_keepalive=True,
            redis_retry_on_timeout=True,
            redis_max_connections=20,
            # Queues / routing
            task_default_queue="default",
            task_default_exchange="default",
            task_default_exchange_type="direct",
            task_default_routing_key="default",
            # Workers
            worker_max_tasks_per_child=1000,
            worker_max_memory_per_child=200_000,
        )
        logger.info("Celery app configuration completed")

    # ---------------------------------------------------------------------
    @staticmethod
    def _setup_task_routes(app: Celery) -> None:
        app.conf.task_routes = {
            "worker.tasks.github_tasks.*": {"queue": "github_api", "priority": 8},
        }

        app.conf.task_queues = {
            "github_api": {
                "exchange": "github_api",
                "exchange_type": "direct",
                "routing_key": "github_api",
            },
            "repo_operations": {
                "exchange": "repo_operations",
                "exchange_type": "direct",
                "routing_key": "repo_operations",
            },
            "deployments": {
                "exchange": "deployments",
                "exchange_type": "direct",
                "routing_key": "deployments",
            },
            "maintenance": {
                "exchange": "maintenance",
                "exchange_type": "direct",
                "routing_key": "maintenance",
            },
        }
        logger.info("Task routing configuration completed")

    # ---------------------------------------------------------------------
    @staticmethod
    def _setup_otel(app: Celery) -> None:
        if not settings.azure_monitor_connection_string:
            logger.info("Azure Monitor not configured, skipping OTEL setup")
            return

        try:
            from opentelemetry.instrumentation.celery import CeleryInstrumentor
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            from opentelemetry import trace
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            resource = Resource(
                attributes={
                    SERVICE_NAME: "devops-agent-worker",
                    "service.version": settings.version,
                    "service.environment": getattr(settings, "environment", "development"),
                }
            )
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(
                BatchSpanProcessor(
                    AzureMonitorTraceExporter.from_connection_string(
                        settings.azure_monitor_connection_string
                    )
                )
            )
            trace.set_tracer_provider(provider)

            CeleryInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            logger.info("OpenTelemetry instrumentation enabled")

        except Exception as exc:  # broad catch for missing deps or misconfig
            logger.warning("OTEL setup failed: %s", exc)


# ───────────────────────────── Create app ─────────────────────────────────
app = CeleryAppFactory.create_app()

# ───────────────────────────── Utility tasks ─────────────────────────────
@app.task(bind=True, name="log_failure_task")
def log_failure_task(self, task_id, error, traceback):
    logger.error("Task failed", task_id=task_id, error=str(error), traceback=traceback)


class CeleryHealthCheck:
    @staticmethod
    def register(app: Celery):
        @app.task(bind=True, queue="maintenance", name="health_check")
        def health(self):
            return {
                "status": "healthy",
                "worker_id": self.request.id,
                "app_name": app.main,
            }

        @app.task(bind=True, queue="github_api", name="github_connection_test")
        def github_connection(self, token: str):
            from gateway.app.services.deployments.github_service import github_service_context

            try:
                with github_service_context(token, timeout=10) as svc:
                    info = svc.validate_and_fetch("octocat/Hello-World")
                return {"status": "connected", "test_repo": info.full_name}
            except Exception as exc:
                logger.error("GitHub connection test failed: %s", exc)
                return {"status": "failed", "error": str(exc)}

CeleryHealthCheck.register(app)

# ───────────────────────────── Signal hooks ──────────────────────────────
@signals.task_prerun.connect
def _prerun(sender=None, task_id=None, task=None, **_):
    logger.info("Starting task", task=sender.name, id=task_id)


@signals.task_postrun.connect
def _postrun(sender=None, task_id=None, state=None, **_):
    logger.info("Finished task", task=sender.name, id=task_id, state=state)


@signals.task_failure.connect
def _on_failure(sender=None, task_id=None, exception=None, **_):
    logger.error("Task failed", task=sender.name, id=task_id, exc=str(exception))

# ───────────────────────────── Banner ────────────────────────────────────
logger.info("Celery '%s' initialised; queues: %s", app.main, ", ".join(app.conf.task_queues))
