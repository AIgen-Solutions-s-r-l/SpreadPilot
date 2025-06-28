from setuptools import setup, find_packages

setup(
    name="spreadpilot-core",
    version="1.1.12.2",
    packages=find_packages(),
    install_requires=[
        # "google-cloud-firestore>=2.11.0", # Removed as part of Firestore -> MongoDB migration
        # "google-cloud-logging>=3.5.0", # Removed as part of logging refactor
        # "google-cloud-secret-manager>=2.16.0", # Removed as part of refactoring to MongoDB secrets
        "motor>=3.4.0",       # Async MongoDB driver (added)
        "pymongo>=4.9.0",     # MongoDB driver (added)
        "ib-insync>=0.9.85",  # IBKR API wrapper
        "pydantic>=2.0.0",    # Data validation
        "opentelemetry-api>=1.18.0,<2.0.0",
        "opentelemetry-sdk>=1.18.0,<2.0.0",
        "opentelemetry-exporter-otlp>=1.18.0,<2.0.0",
        "pandas>=2.0.0",      # Data manipulation
        "openpyxl>=3.1.2",    # Excel generation
        "reportlab>=4.0.4",   # PDF generation
        "sendgrid>=6.10.0",   # Email sending
        "python-telegram-bot>=20.3",  # Telegram integration
        "pytz>=2023.3",       # Timezone handling
        "aiohttp>=3.8.5",     # Async HTTP
        "docker>=6.0.0",      # Docker API client
        "backoff>=2.2.0",     # Exponential backoff utilities
        "hvac>=2.0.0",        # HashiCorp Vault client
        "apscheduler>=3.10.0", # Advanced Python Scheduler
        "redis>=5.0.0",       # Redis client
        "gspread>=5.11.0",    # Google Sheets API wrapper
        "google-cloud-storage>=2.10.0",  # GCS for file storage
    ],
    python_requires=">=3.11",
    author="SpreadPilot Team",
    author_email="capital@tradeautomation.it",
    description="Core library for SpreadPilot platform",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)