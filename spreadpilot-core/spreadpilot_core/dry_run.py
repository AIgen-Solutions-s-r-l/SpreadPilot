"""Dry-run mode framework for SpreadPilot.

This module provides a decorator-based system for simulating operations
without actually executing them. Useful for validation, testing, and training.
"""

import functools
import inspect
import logging
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DryRunConfig:
    """Global dry-run configuration."""

    _enabled = False
    _log_operations = True
    _collect_reports = True
    _operations_log = []

    @classmethod
    def enable(cls):
        """Enable dry-run mode globally."""
        cls._enabled = True
        logger.info("🔵 DRY-RUN MODE ENABLED - No operations will be executed")

    @classmethod
    def disable(cls):
        """Disable dry-run mode globally."""
        cls._enabled = False
        logger.info("✅ DRY-RUN MODE DISABLED - Operations will execute normally")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if dry-run mode is enabled."""
        return cls._enabled

    @classmethod
    def log_operation(cls, operation: dict):
        """Log a dry-run operation."""
        if cls._collect_reports:
            cls._operations_log.append(operation)

    @classmethod
    def get_operations_log(cls) -> list:
        """Get all logged operations."""
        return cls._operations_log.copy()

    @classmethod
    def clear_operations_log(cls):
        """Clear operations log."""
        cls._operations_log.clear()

    @classmethod
    def get_report(cls) -> dict:
        """Get dry-run execution report."""
        operations_by_type = {}
        for op in cls._operations_log:
            op_type = op.get("type", "unknown")
            if op_type not in operations_by_type:
                operations_by_type[op_type] = []
            operations_by_type[op_type].append(op)

        return {
            "total_operations": len(cls._operations_log),
            "operations_by_type": {
                k: len(v) for k, v in operations_by_type.items()
            },
            "operations": cls._operations_log,
            "generated_at": datetime.utcnow().isoformat(),
        }


def dry_run(
    operation_type: str,
    return_value: Any = None,
    log_args: bool = True,
):
    """Decorator for dry-run operations.

    When dry-run mode is enabled, the decorated function will not execute.
    Instead, it logs what would have been done and returns a default value.

    Args:
        operation_type: Type of operation (e.g., "trade", "database", "email")
        return_value: Value to return when in dry-run mode
        log_args: Whether to log function arguments

    Example:
        @dry_run("trade", return_value={"order_id": "DRY_RUN_12345"})
        def place_order(symbol, quantity):
            # Real implementation
            return ibkr_client.place_order(symbol, quantity)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not DryRunConfig.is_enabled():
                # Execute normally
                return func(*args, **kwargs)

            # Dry-run mode: log and return mock value
            func_name = func.__name__
            module_name = func.__module__

            # Build operation log
            operation = {
                "type": operation_type,
                "function": f"{module_name}.{func_name}",
                "timestamp": datetime.utcnow().isoformat(),
            }

            if log_args:
                # Get argument names
                sig = inspect.signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                bound_args.apply_defaults()

                # Filter out 'self' and 'cls'
                operation["arguments"] = {
                    k: v
                    for k, v in bound_args.arguments.items()
                    if k not in ("self", "cls")
                }

            # Log operation
            logger.info(
                f"[DRY-RUN] {operation_type.upper()}: {func_name} - "
                f"Would execute with args: {operation.get('arguments', {})}"
            )

            DryRunConfig.log_operation(operation)

            return return_value

        return wrapper

    return decorator


def dry_run_async(
    operation_type: str,
    return_value: Any = None,
    log_args: bool = True,
):
    """Async version of dry_run decorator.

    Example:
        @dry_run_async("database", return_value=True)
        async def save_to_db(data):
            await db.collection.insert_one(data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not DryRunConfig.is_enabled():
                # Execute normally
                return await func(*args, **kwargs)

            # Dry-run mode: log and return mock value
            func_name = func.__name__
            module_name = func.__module__

            # Build operation log
            operation = {
                "type": operation_type,
                "function": f"{module_name}.{func_name}",
                "timestamp": datetime.utcnow().isoformat(),
            }

            if log_args:
                sig = inspect.signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                bound_args.apply_defaults()

                operation["arguments"] = {
                    k: v
                    for k, v in bound_args.arguments.items()
                    if k not in ("self", "cls")
                }

            logger.info(
                f"[DRY-RUN] {operation_type.upper()}: {func_name} - "
                f"Would execute with args: {operation.get('arguments', {})}"
            )

            DryRunConfig.log_operation(operation)

            return return_value

        return wrapper

    return decorator


# Specialized decorators for common operations


def dry_run_trade(return_value: Optional[dict] = None):
    """Decorator for trading operations.

    Example:
        @dry_run_trade(return_value={"order_id": "DRY_123", "status": "FILLED"})
        def place_order(symbol, quantity):
            return ibkr.place_order(symbol, quantity)
    """
    if return_value is None:
        return_value = {
            "order_id": f"DRY_RUN_{int(datetime.utcnow().timestamp())}",
            "status": "DRY_RUN",
            "message": "Order not placed (dry-run mode)",
        }
    return dry_run("trade", return_value=return_value)


def dry_run_database(return_value: Any = True):
    """Decorator for database operations.

    Example:
        @dry_run_database()
        def update_position(position_id, data):
            return db.positions.update_one({"_id": position_id}, data)
    """
    return dry_run("database", return_value=return_value)


def dry_run_database_async(return_value: Any = True):
    """Async decorator for database operations.

    Example:
        @dry_run_database_async()
        async def save_order(order_data):
            await db.orders.insert_one(order_data)
    """
    return dry_run_async("database", return_value=return_value)


def dry_run_email(return_value: Any = True):
    """Decorator for email operations.

    Example:
        @dry_run_email()
        def send_alert_email(to, subject, body):
            return email_client.send(to, subject, body)
    """
    return dry_run("email", return_value=return_value)


def dry_run_notification(return_value: Any = True):
    """Decorator for notification operations (Telegram, etc).

    Example:
        @dry_run_notification()
        def send_telegram(message):
            return telegram_bot.send_message(chat_id, message)
    """
    return dry_run("notification", return_value=return_value)


def dry_run_api_call(return_value: Any = None):
    """Decorator for external API calls.

    Example:
        @dry_run_api_call(return_value={"success": True})
        def call_external_api(endpoint, data):
            return httpx.post(endpoint, json=data)
    """
    return dry_run("api_call", return_value=return_value)


# Context manager for temporary dry-run mode


class dry_run_context:
    """Context manager for temporary dry-run mode.

    Example:
        with dry_run_context():
            # These operations will be simulated
            place_order("QQQ", 100)
            send_email("alert@example.com", "Test")

        # Back to normal execution
    """

    def __init__(self):
        self.was_enabled = False

    def __enter__(self):
        self.was_enabled = DryRunConfig.is_enabled()
        DryRunConfig.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.was_enabled:
            DryRunConfig.disable()
