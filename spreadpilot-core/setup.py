from setuptools import setup, find_packages

setup(
    name="spreadpilot-core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-cloud-firestore>=2.11.0",
        "google-cloud-logging>=3.5.0",
        # "google-cloud-secret-manager>=2.16.0", # Removed as part of refactoring to MongoDB secrets
        "ib-insync>=0.9.85",  # IBKR API wrapper
        "pydantic>=2.0.0",    # Data validation
        "opentelemetry-api>=1.18.0",
        "opentelemetry-sdk>=1.18.0",
        "opentelemetry-exporter-otlp>=1.18.0",
        "pandas>=2.0.0",      # Data manipulation
        "openpyxl>=3.1.2",    # Excel generation
        "reportlab>=4.0.4",   # PDF generation
        "sendgrid>=6.10.0",   # Email sending
        "python-telegram-bot>=20.3",  # Telegram integration
        "pytz>=2023.3",       # Timezone handling
        "aiohttp>=3.8.5",     # Async HTTP
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