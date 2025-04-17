"""SpreadPilot Trading Bot.

This is the main entry point for the trading bot service, which:
1. Connects to IBKR
2. Polls Google Sheets for signals
3. Executes orders
4. Monitors positions for assignments
5. Calculates P&L
"""

import asyncio
import os
import signal
import sys
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from spreadpilot_core.logging import get_logger, setup_logging
from spreadpilot_core.models import Follower, Position, Trade, Alert, AlertType, AlertSeverity

from .config import Settings, get_settings
from .service import TradingService
from .sheets import GoogleSheetsClient

# Initialize logger
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SpreadPilot Trading Bot",
    description="Trading bot for SpreadPilot platform",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
settings: Optional[Settings] = None
trading_service: Optional[TradingService] = None
sheets_client: Optional[GoogleSheetsClient] = None
shutdown_event: Optional[asyncio.Event] = None


class TradeSignal(BaseModel):
    """Trade signal model."""

    strategy: str
    qty_per_leg: int
    strike_long: float
    strike_short: float
    follower_id: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global settings, trading_service, sheets_client, shutdown_event
    
    # Set up logging
    setup_logging(
        service_name="trading-bot",
        enable_gcp=True,
        enable_otlp=True,
    )
    
    # Load settings
    settings = get_settings()
    
    # Create shutdown event
    shutdown_event = asyncio.Event()
    
    # Initialize Google Sheets client
    sheets_client = GoogleSheetsClient(
        sheet_url=settings.google_sheet_url,
        api_key=settings.google_sheets_api_key,
    )
    
    # Initialize trading service
    trading_service = TradingService(
        settings=settings,
        sheets_client=sheets_client,
    )
    
    # Start background tasks
    asyncio.create_task(trading_service.run(shutdown_event))
    
    logger.info("Trading bot started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down trading bot")
    
    # Signal shutdown to background tasks
    if shutdown_event:
        shutdown_event.set()
    
    # Wait for background tasks to complete
    if trading_service:
        await trading_service.shutdown()
    
    logger.info("Trading bot shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not trading_service or not trading_service.is_healthy():
        raise HTTPException(status_code=503, detail="Trading bot is not healthy")
    
    return {"status": "healthy"}


@app.get("/status")
async def get_status():
    """Get trading bot status."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")
    
    return {
        "status": trading_service.get_status(),
        "ibkr_connected": trading_service.is_ibkr_connected(),
        "sheets_connected": trading_service.is_sheets_connected(),
        "active_followers": trading_service.get_active_follower_count(),
    }


@app.post("/trade/signal")
async def process_trade_signal(signal: TradeSignal):
    """Process a trade signal manually."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")
    
    logger.info(
        "Received manual trade signal",
        strategy=signal.strategy,
        qty_per_leg=signal.qty_per_leg,
        strike_long=signal.strike_long,
        strike_short=signal.strike_short,
        follower_id=signal.follower_id,
    )
    
    # Process signal
    result = await trading_service.signal_processor.process_signal(
        strategy=signal.strategy,
        qty_per_leg=signal.qty_per_leg,
        strike_long=signal.strike_long,
        strike_short=signal.strike_short,
        follower_id=signal.follower_id,
    )
    
    return result


@app.post("/close/{follower_id}")
async def close_positions(follower_id: str):
    """Close all positions for a follower."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")
    
    logger.info("Closing positions for follower", follower_id=follower_id)
    
    # Close positions
    result = await trading_service.close_positions(follower_id)
    
    return result


@app.post("/close/all")
async def close_all_positions():
    """Close all positions for all followers."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")
    
    logger.info("Closing all positions for all followers")
    
    # Close all positions
    result = await trading_service.close_all_positions()
    
    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def handle_sigterm(signum, frame):
    """Handle SIGTERM signal."""
    logger.info("Received SIGTERM")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Run the application
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=os.environ.get("ENV", "production") == "development",
    )