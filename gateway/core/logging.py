from __future__ import annotations

import logging
import os
from typing import List

import structlog
from opentelemetry.trace import get_current_span
from gateway.config import Settings

# Import OpenTelemetry logging handler
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor


def _add_trace_context(logger, method_name, event_dict):
    """Inject trace_id / span_id if a span is active."""
    span = get_current_span()
    if span and span.get_span_context().is_valid:
        sc = span.get_span_context()
        event_dict["trace_id"] = format(sc.trace_id, "032x")
        event_dict["span_id"] = format(sc.span_id, "016x")
    return event_dict


def _processors(dev: bool) -> List:
    shared = [
        structlog.processors.TimeStamper(fmt="iso"),
        _add_trace_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    return shared + (
        [structlog.dev.ConsoleRenderer()]
        if dev
        else [structlog.processors.JSONRenderer()]
    )


def setup_logging(*, debug: bool = False) -> None:
    """Configure structured logging with optional Azure Monitor export."""
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    structlog.configure(
        processors=_processors(debug),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Azure Monitor log exporter
    conn = Settings().AZURE_MONITOR_CONNECTION_STRING
    if conn:
        # Set up OpenTelemetry LoggerProvider
        logger_provider = LoggerProvider()
        exporter = AzureMonitorLogExporter.from_connection_string(conn)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        logging.getLogger().addHandler(LoggingHandler(logger_provider=logger_provider))


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Factory used everywhere else."""
    return structlog.get_logger(name)