# SpreadPilot Documentation

Welcome to the SpreadPilot documentation. This directory contains comprehensive documentation for the SpreadPilot system, a copy-trading platform for QQQ options strategies.

## Documentation Structure

The documentation is organized into the following sections:

1. [System Architecture](./01-system-architecture.md) - Overview of the system components and how they interact
2. [Deployment Guide](./02-deployment-guide.md) - Instructions for deploying the system to Google Cloud Platform
3. [Development Guide](./03-development-guide.md) - Guide for local development, testing, and code organization
4. [Operations Guide](./04-operations-guide.md) - Instructions for monitoring, maintaining, and troubleshooting the system

## Diagrams

The `images/` directory contains diagrams referenced in the documentation:

- `system-architecture.png` - High-level system architecture diagram
- `reference-architecture.png` - Detailed reference architecture diagram

## Additional Resources

- [Project README](../README.md) - Project overview and quick start guide
- [SpreadPilot Core README](../spreadpilot-core/README.md) - Documentation for the core library
- [Trading Bot README](../trading-bot/README.md) - Documentation for the trading bot service

## Folder Structure Convention

SpreadPilot uses hyphenated directory names (`trading-bot`, `admin-api`, etc.) for all services. These directories are made importable as Python packages through `__init__.py` files. When importing from these directories in Python code, use the `importlib.import_module()` function:

```python
# Example: Importing from hyphenated directories
import importlib

# Import the entire module
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')

# Import specific components
SignalProcessor = trading_bot_service.SignalProcessor
```

This approach allows us to maintain a consistent naming convention across deployment and testing environments while still supporting Python imports.

## Contributing to Documentation

To contribute to this documentation:

1. Make your changes to the relevant Markdown files
2. Update diagrams if necessary (diagrams are created using [Mermaid](https://mermaid-js.github.io/mermaid/))
3. Submit a pull request with your changes

## License

This documentation is proprietary and confidential. All rights reserved.
