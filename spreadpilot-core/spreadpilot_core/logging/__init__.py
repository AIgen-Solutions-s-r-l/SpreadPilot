"""Logging module for SpreadPilot.

This module provides structured logging with OpenTelemetry and GCP Cloud Logging integration.
"""

from .logger import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]