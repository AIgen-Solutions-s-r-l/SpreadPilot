# SpreadPilot Trading Bot

This is the trading bot service for the SpreadPilot platform. It's responsible for:

1. Connecting to Interactive Brokers (IBKR)
2. Polling Google Sheets for trading signals
3. Executing vertical spread orders
4. Monitoring positions for assignments
5. Calculating P&L

## Architecture

The trading bot is built as a FastAPI application with a modular service structure:

- `app/main.py`: FastAPI application entry point
- `app/config.py`: Configuration settings
- `app/sheets.py`: Google Sheets client
- `app/service/`: Modular service components
  - `base.py`: Core TradingService class
  - `ibkr.py`: IBKR client interaction
  - `signals.py`: Signal processing
  - `positions.py`: Position management and assignment handling
  - `alerts.py`: Alert creation and notification

## API Endpoints

- `GET /health`: Health check endpoint
- `GET /status`: Get trading bot status
- `POST /trade/signal`: Process a trade signal manually
- `POST /close/{follower_id}`: Close all positions for a follower
- `POST /close/all`: Close all positions for all followers

## Development

### Prerequisites

- Python 3.11
- Interactive Brokers Gateway
- Google Sheets API access

### Import Pattern

The trading bot service uses a hyphenated directory name (`trading-bot`) which is made importable as a Python package through `__init__.py` files. When importing from this directory in other parts of the codebase (like tests), use the `importlib.import_module()` function:

```python
# Example: Importing from the trading-bot directory
import importlib

# Import the entire module
trading_bot_service = importlib.import_module('trading-bot.app.service.signals')
trading_bot_sheets = importlib.import_module('trading-bot.app.sheets')

# Import specific components
SignalProcessor = trading_bot_service.SignalProcessor
GoogleSheetsClient = trading_bot_sheets.GoogleSheetsClient
```

### Setup

1. Install dependencies:

```bash
pip install -e ../spreadpilot-core
pip install fastapi uvicorn
```

2. Run the application:

```bash
uvicorn app.main:app --reload
```

## Deployment

The service is containerized using Docker and deployed on Google Cloud Run.

```bash
# Build the Docker image
docker build -t gcr.io/spreadpilot/trading-bot:latest -f Dockerfile ..

# Run the container locally
docker run -p 8080:8080 gcr.io/spreadpilot/trading-bot:latest

# Push to Google Container Registry
docker push gcr.io/spreadpilot/trading-bot:latest