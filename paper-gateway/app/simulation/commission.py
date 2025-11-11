"""Commission calculation for paper trading."""

from ..config import get_settings
from ..models import AssetType


def calculate_commission(
    quantity: int,
    price: float,
    asset_type: AssetType,
) -> float:
    """Calculate commission based on IBKR fee schedule.

    IBKR Commission Structure:
    - Stocks: $0.005 per share, min $1, max 1% of trade value
    - Options: $0.65 per contract

    Args:
        quantity: Number of shares/contracts
        price: Price per share/contract
        asset_type: STOCK or OPTION

    Returns:
        Commission amount in USD
    """
    settings = get_settings()

    if asset_type == AssetType.STOCK:
        # Stock commission: $0.005 per share
        commission = quantity * settings.paper_commission_rate

        # Minimum $1
        commission = max(commission, 1.0)

        # Maximum 1% of trade value
        trade_value = quantity * price
        max_commission = trade_value * 0.01
        commission = min(commission, max_commission)

    elif asset_type == AssetType.OPTION:
        # Option commission: $0.65 per contract
        commission = quantity * settings.paper_option_commission

    else:
        raise ValueError(f"Unknown asset type: {asset_type}")

    return round(commission, 2)


def calculate_slippage(
    quantity: int,
    price: float,
    action: str,
) -> float:
    """Calculate slippage amount.

    Uses square root market impact model:
    slippage_bps = base_bps * sqrt(quantity / liquidity_threshold)

    Args:
        quantity: Order quantity
        price: Current price
        action: BUY or SELL

    Returns:
        Slippage amount in USD (total, not per share)
    """
    settings = get_settings()

    # Liquidity threshold (orders above this see more slippage)
    liquidity_threshold = 1000

    # Base slippage in basis points
    base_slippage_bps = settings.paper_slippage_bps

    # Square root impact model
    slippage_bps = base_slippage_bps * (quantity / liquidity_threshold) ** 0.5

    # Cap at 20 bps
    slippage_bps = min(slippage_bps, 20.0)

    # Convert to dollar amount
    # BUY: slippage increases cost (positive)
    # SELL: slippage decreases proceeds (positive cost to us)
    slippage_per_share = (slippage_bps / 10000.0) * price
    total_slippage = slippage_per_share * quantity

    return round(total_slippage, 2)
