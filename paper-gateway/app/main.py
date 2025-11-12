"""Main FastAPI application for paper trading gateway."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .models import (AccountInfo, BalanceUpdateRequest, HealthResponse,
                     OrderRequest, OrderResponse, PerformanceMetrics, Position)
from .simulation.execution_simulator import get_execution_simulator
from .simulation.market_hours import get_market_status, is_market_open
from .storage.mongo import get_mongo_client
from .storage.state import get_state_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting paper trading gateway...")
    settings = get_settings()
    logger.info(f"Configuration: {settings.dict()}")

    # Connect to MongoDB
    mongo = get_mongo_client()
    await mongo.connect()
    logger.info("Connected to MongoDB")

    # Initialize account
    state_manager = get_state_manager()
    await state_manager.initialize_account()
    logger.info("Account initialized")

    yield

    # Shutdown
    logger.info("Shutting down paper trading gateway...")
    await mongo.disconnect()
    logger.info("Disconnected from MongoDB")


# Create FastAPI app
app = FastAPI(
    title="SpreadPilot Paper Trading Gateway",
    description="Mock IBKR Gateway for paper trading with realistic market simulation",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
# Load CORS origins from environment variable or use secure defaults
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Default to localhost for development only
    # In production, MUST set CORS_ORIGINS environment variable
    cors_origins = ["http://localhost:3000", "http://localhost:8080"]
    logger.warning(
        "CORS_ORIGINS not set - using development defaults. "
        "Set CORS_ORIGINS environment variable in production!"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="Paper Trading Gateway",
        version=__version__,
        market_open=is_market_open(),
        timestamp=datetime.utcnow(),
    )


@app.get("/api/v1/market/status")
async def market_status():
    """Get current market status."""
    return get_market_status()


# Orders API
@app.post("/api/v1/orders", response_model=OrderResponse)
async def place_order(order_request: OrderRequest):
    """Place a paper trading order.

    Args:
        order_request: Order details

    Returns:
        Order response with execution details
    """
    logger.info(f"Placing order: {order_request.dict()}")

    state_manager = get_state_manager()
    execution_simulator = get_execution_simulator()

    # Generate order ID
    import time

    order_id = f"PAPER_{int(time.time() * 1000)}"

    # Get account to check funds
    account = await state_manager.get_account()

    # Simulate execution
    (
        status,
        fill_price,
        filled_quantity,
        commission,
        slippage,
        rejection_reason,
    ) = execution_simulator.simulate_order_execution(
        symbol=order_request.symbol,
        action=order_request.action,
        quantity=order_request.quantity,
        order_type=order_request.order_type,
        limit_price=order_request.limit_price,
        asset_type=order_request.asset_type,
        strike=order_request.strike,
        expiry=order_request.expiry,
        option_type=order_request.option_type,
    )

    # Check affordability for BUY orders
    if status.value == "FILLED" or status.value == "PARTIAL":
        if order_request.action.value == "BUY":
            can_afford, afford_reason = execution_simulator.can_afford_order(
                cash_balance=account.cash_balance,
                action=order_request.action,
                quantity=filled_quantity,
                estimated_price=fill_price,
                asset_type=order_request.asset_type,
            )

            if not can_afford:
                status = "REJECTED"
                rejection_reason = afford_reason
                fill_price = None
                filled_quantity = 0

    # Save order
    from .models import OrderDocument
    from .models import OrderStatus as OrderStatusEnum

    order_doc = OrderDocument(
        order_id=order_id,
        symbol=order_request.symbol,
        action=order_request.action.value,
        quantity=order_request.quantity,
        order_type=order_request.order_type.value,
        limit_price=order_request.limit_price,
        status=status.value if isinstance(status, OrderStatusEnum) else status,
        fill_price=fill_price,
        filled_quantity=filled_quantity,
        commission=commission,
        slippage=slippage,
        timestamp=datetime.utcnow(),
        rejection_reason=rejection_reason,
        asset_type=order_request.asset_type.value,
        strike=order_request.strike,
        expiry=order_request.expiry,
        option_type=order_request.option_type.value if order_request.option_type else None,
    )

    await state_manager.save_order(order_doc)

    # Update account and positions if filled
    if status.value == "FILLED" or status.value == "PARTIAL":
        # Update cash balance
        if order_request.action.value == "BUY":
            cash_delta = -(filled_quantity * fill_price + commission)
        else:  # SELL
            cash_delta = filled_quantity * fill_price - commission

        await state_manager.update_account_balance(cash_delta, commission)

        # Update position
        await state_manager.update_position(
            symbol=order_request.symbol,
            action=order_request.action,
            quantity=filled_quantity,
            fill_price=fill_price,
            asset_type=order_request.asset_type,
            strike=order_request.strike,
            expiry=order_request.expiry,
            option_type=order_request.option_type.value if order_request.option_type else None,
        )

    logger.info(f"Order {order_id}: {status.value}, filled={filled_quantity}, price=${fill_price}")

    # Return response
    return OrderResponse(
        order_id=order_id,
        symbol=order_request.symbol,
        action=order_request.action,
        quantity=order_request.quantity,
        order_type=order_request.order_type,
        limit_price=order_request.limit_price,
        status=status,
        fill_price=fill_price,
        filled_quantity=filled_quantity,
        commission=commission,
        timestamp=order_doc.timestamp,
        rejection_reason=rejection_reason,
    )


@app.get("/api/v1/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Get order by ID.

    Args:
        order_id: Order ID

    Returns:
        Order details
    """
    state_manager = get_state_manager()
    order = await state_manager.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    from .models import OrderAction
    from .models import OrderStatus as OrderStatusEnum
    from .models import OrderType

    return OrderResponse(
        order_id=order.order_id,
        symbol=order.symbol,
        action=OrderAction(order.action),
        quantity=order.quantity,
        order_type=OrderType(order.order_type),
        limit_price=order.limit_price,
        status=OrderStatusEnum(order.status),
        fill_price=order.fill_price,
        filled_quantity=order.filled_quantity,
        commission=order.commission,
        timestamp=order.timestamp,
        rejection_reason=order.rejection_reason,
    )


# Positions API
@app.get("/api/v1/positions", response_model=list[Position])
async def get_positions():
    """Get all current positions.

    Returns:
        List of positions with current market values
    """
    state_manager = get_state_manager()
    positions = await state_manager.get_all_positions()
    return positions


@app.post("/api/v1/positions/{symbol}/close")
async def close_position(symbol: str):
    """Close a position.

    Args:
        symbol: Symbol to close

    Returns:
        Closing order details
    """
    state_manager = get_state_manager()
    position = await state_manager.get_position(symbol)

    if not position:
        raise HTTPException(status_code=404, detail=f"Position {symbol} not found")

    # Create closing order
    from .models import AssetType, OrderAction
    from .models import OrderType as OrderTypeEnum

    order_request = OrderRequest(
        symbol=symbol,
        action=OrderAction.SELL if position.quantity > 0 else OrderAction.BUY,
        quantity=abs(position.quantity),
        order_type=OrderTypeEnum.MARKET,
        asset_type=AssetType(position.asset_type),
        strike=position.strike,
        expiry=position.expiry,
        option_type=position.option_type,
    )

    return await place_order(order_request)


# Account API
@app.get("/api/v1/account", response_model=AccountInfo)
async def get_account():
    """Get account information.

    Returns:
        Account details with current values
    """
    state_manager = get_state_manager()
    return await state_manager.get_account_info()


@app.get("/api/v1/account/summary", response_model=AccountInfo)
async def get_account_summary():
    """Get account summary (alias for /account).

    Returns:
        Account details
    """
    return await get_account()


# Performance API
@app.get("/api/v1/account/performance", response_model=PerformanceMetrics)
async def get_performance():
    """Get performance metrics.

    Returns:
        Performance statistics
    """
    state_manager = get_state_manager()
    return await state_manager.get_performance_metrics()


# Admin API
@app.post("/api/v1/admin/reset")
async def reset_account():
    """Reset paper trading account to initial state.

    This is an admin function for testing/demos.

    Returns:
        Success message
    """
    logger.warning("Resetting paper trading account")
    state_manager = get_state_manager()
    await state_manager.reset_account()

    return {
        "success": True,
        "message": "Paper trading account reset to initial state",
    }


@app.put("/api/v1/admin/balance")
async def update_balance(request: BalanceUpdateRequest):
    """Update account balance (admin function).

    Args:
        request: New balance

    Returns:
        Updated account info
    """
    logger.warning(f"Updating balance to ${request.new_balance}")
    state_manager = get_state_manager()
    await state_manager.set_balance(request.new_balance)

    return await get_account()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4003)
