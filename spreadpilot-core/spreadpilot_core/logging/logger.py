"""Logging module for SpreadPilot."""

import logging
import os
import sys

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure default logging format
_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Global flag to track if logging has been set up
_LOGGING_SETUP_DONE = False


def setup_logging(
    service_name: str,
    log_level: int = logging.INFO,
    # enable_gcp: bool = True, # Removed GCP flag
    enable_otlp: bool = True,
    otlp_endpoint: str | None = None,
) -> None:
    """Set up logging for the application.

    Args:
        service_name: Name of the service (e.g., "trading-bot")
        log_level: Logging level (default: INFO)
        # enable_gcp: Whether to enable GCP Cloud Logging (Removed)
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

    # GCP Cloud Logging setup removed

    # Set up OpenTelemetry tracing if enabled
    if enable_otlp:
        try:
            resource = Resource.create({"service.name": service_name})
            trace.set_tracer_provider(TracerProvider(resource=resource))

            # Configure the OTLP exporter
            endpoint = otlp_endpoint or os.environ.get(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            )
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)

            logging.info(f"OpenTelemetry tracing enabled, exporting to {endpoint}")
        except Exception as e:
            logging.warning(f"Failed to set up OpenTelemetry tracing: {e}")

    _LOGGING_SETUP_DONE = True
    logging.info(f"Logging setup complete for service: {service_name}")


# StructuredLogger class removed as it was primarily for GCP JSON formatting.
# Standard logging configured via basicConfig is sufficient.


def get_logger(name: str) -> logging.Logger:
    """Get a standard Python logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Standard logging.Logger instance
    """
    # Ensure setup is called at least once (idempotent)
    # This might be better placed in application entry points,
    # but keeping it here for minimal changes for now.
    # Consider moving setup_logging calls to main.py of each service.
    if not _LOGGING_SETUP_DONE:
        # Attempt basic setup if not done, assuming default service name if needed
        # This is a fallback, explicit setup in app entry points is preferred.
        setup_logging(service_name=name.split(".")[0] or "unknown_service")

    return logging.getLogger(name)
