"""Utility functions for SpreadPilot.

This module provides utility functions for report generation, alerts, etc.
"""

from .email import send_email
from .excel import generate_excel_report
from .pdf import generate_pdf_report
from .telegram import send_telegram_message
from .time import get_ny_time, is_market_open
from .vault import VaultClient, get_ibkr_credentials_from_vault, get_vault_client

__all__ = [
    "VaultClient",
    "generate_excel_report",
    "generate_pdf_report",
    "get_ibkr_credentials_from_vault",
    "get_ny_time",
    "get_vault_client",
    "is_market_open",
    "send_email",
    "send_telegram_message",
]
