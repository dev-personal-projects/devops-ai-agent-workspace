from __future__ import annotations

import os
from celery import Celery
from gateway.config import settings
from gateway.core.logging import setup_logging, get_logger
from typing import Optional

# Setup logging for worker
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


class CeleryAppFactory:
    """Factory for creating Celery app - Single Responsibility Principle"""
    
    @staticmethod
    def create_app(name: str = "devops-agent") -> Celery:
        """Create and configure Celery app"""
        app = Celery(
            name,
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
            include=[
                "worker.tasks.repo_scan",
                "worker.tasks.deploy",
            ]
        )
        
        CeleryAppFactory._configure_app(app)
        CeleryAppFactory._setup_telemetry(app)
        
        return app
    
    @staticmethod
    def _configure_app(app: Celery) -> None:
        """Configure Celery app settings"""
        app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=1800,  # 30 minutes max per task
            task_soft_time_limit=1500,  # 25 minutes soft limit
            worker_prefetch_multiplier=1,
            result_expires=3600,  # 1 hour
        )
        logger.info("Celery app configuration completed")
    
    @staticmethod
    def _setup_telemetry(app: Celery) -> None:
        """Setup OpenTelemetry for Celery if configured"""
        if not settings.azure_monitor_connection_string:
            logger.info("Azure Monitor not configured, skipping telemetry setup")
            return
        
        try:
            from opentelemetry.instrumentation.celery import CeleryInstrumentor
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            
            resource = Resource(attributes={SERVICE_NAME: "devops-agent-worker"})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(
                AzureMonitorTraceExporter.from_connection_string(
                    settings.azure_monitor_connection_string
                )
            )
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            
            CeleryInstrumentor().instrument()
            logger.info("Celery OpenTelemetry instrumentation enabled")
            
        except ImportError as e:
            logger.warning(f"OpenTelemetry dependencies not installed: {e}")
        except Exception as e:
            logger.error(f"Failed to setup telemetry: {e}")


class CeleryHealthCheck:
    """Health check utilities for Celery - Single Responsibility Principle"""
    
    @staticmethod
    def create_health_check_task(app: Celery):
        """Create health check task for the app"""
        @app.task(bind=True)
        def health_check(self):
            """Simple health check task"""
            return {
                "status": "healthy", 
                "worker_id": self.request.id,
                "app_name": app.main
            }
        return health_check


# Create the Celery app using the factory
app = CeleryAppFactory.create_app()

# Add health check task
health_check = CeleryHealthCheck.create_health_check_task(app)

logger.info(f"Celery app '{app.main}' initialized successfully")
logger.info(f"Broker: {settings.celery_broker_url}")
logger.info(f"Backend: {settings.celery_result_backend}")