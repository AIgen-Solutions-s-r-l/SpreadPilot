"""Logging module for SpreadPilot."""

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from google.cloud import logging as gcp_logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure default logging format
_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Global flag to track if logging has been set up
_LOGGING_SETUP_DONE = False


def setup_logging(
    service_name: str,
    log_level: int = logging.INFO,
    enable_gcp: bool = True,
    enable_otlp: bool = True,
    otlp_endpoint: Optional[str] = None,
) -> None:
    """Set up logging for the application.

    Args:
        service_name: Name of the service (e.g., "trading-bot")
        log_level: Logging level (default: INFO)
        enable_gcp: Whether to enable GCP Cloud Logging
        enable_otlp: Whether to enable OpenTelemetry tracing
        otlp_endpoint: OpenTelemetry collector endpoint
    """
    global _LOGGING_SETUP_DONE
    if _LOGGING_SETUP_DONE:
        return

    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format=_DEFAULT_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set up GCP Cloud Logging if enabled
    if enable_gcp and os.environ.get("GOOGLE_CLOUD_PROJECT"):
        try:
            client = gcp_logging.Client()
            client.setup_logging(log_level=log_level)
            logging.info("GCP Cloud Logging enabled")
        except Exception as e:
            logging.warning(f"Failed to set up GCP Cloud Logging: {e}")

    # Set up OpenTelemetry tracing if enabled
    if enable_otlp:
        try:
            resource = Resource.create({"service.name": service_name})
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            # Configure the OTLP exporter
            endpoint = otlp_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            logging.info(f"OpenTelemetry tracing enabled, exporting to {endpoint}")
        except Exception as e:
            logging.warning(f"Failed to set up OpenTelemetry tracing: {e}")

    _LOGGING_SETUP_DONE = True
    logging.info(f"Logging setup complete for service: {service_name}")


class StructuredLogger:
    """Logger that outputs structured logs compatible with GCP Cloud Logging."""

    def __init__(self, name: str):
        """Initialize the logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)
        self.tracer = trace.get_tracer(name)

    def _log(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log a message with structured data.

        Args:
            level: Logging level
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        # Extract exc_info before processing kwargs
        include_exc_info = kwargs.pop('exc_info', False)

        # Combine extra and kwargs
        log_data = {}
        if extra:
            log_data.update(extra)
        if kwargs:
            log_data.update(kwargs)

        # Get current span context for trace correlation
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            log_data["trace_id"] = format(span_context.trace_id, "032x")
            log_data["span_id"] = format(span_context.span_id, "016x")

        # Log the message with structured data. Let the standard handler handle exc_info.
        if log_data:
            self.logger.log(level, f"{msg} {json.dumps(log_data)}", exc_info=include_exc_info)
        else:
            self.logger.log(level, msg, exc_info=include_exc_info)

    def debug(self, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.DEBUG, msg, extra, **kwargs)

    def info(self, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.INFO, msg, extra, **kwargs)

    def warning(self, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.WARNING, msg, extra, **kwargs)

    def error(self, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.ERROR, msg, extra, **kwargs)

    def critical(self, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log a critical message.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.CRITICAL, msg, extra, **kwargs)


    def exception(self, msg: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = True, **kwargs: Any) -> None:
        """Log an error message with exception information.

        Args:
            msg: Log message
            extra: Extra data to include in the log
            exc_info: Whether to include exception information (default: True)
            **kwargs: Additional key-value pairs to include in the log
        """
        self._log(logging.ERROR, msg, extra, exc_info=exc_info, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)