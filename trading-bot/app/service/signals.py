"""Signal processor for SpreadPilot trading service."""

import datetime
import uuid
from typing import Dict, Optional, Any

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import (
    AlertType,
    AlertSeverity,
    Trade,
    TradeSide,
    TradeStatus,
)

logger = get_logger(__name__)


class SignalProcessor:
    """Processor for trading signals."""

    def __init__(self, service):
        """Initialize the signal processor.

        Args:
            service: Trading service instance
        """
        self.service = service
        
        logger.info("Initialized signal processor")

    async def process_signal(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        follower_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a trading signal.

        Args:
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg
            follower_id: Follower ID (optional, if None process for all active followers)

        Returns:
            Dict with processing results
        """
        # If follower_id is provided, process for that follower only
        if follower_id:
            if follower_id not in self.service.active_followers:
                logger.error(f"Follower not found or not active: {follower_id}")
                return {
                    "success": False,
                    "error": f"Follower not found or not active: {follower_id}",
                }
            
            return await self._process_signal_for_follower(
                follower_id=follower_id,
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )
        
        # Process for all active followers
        results = {}
        for follower_id in self.service.active_followers:
            results[follower_id] = await self._process_signal_for_follower(
                follower_id=follower_id,
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )
        
        return {
            "success": True,
            "results": results,
        }

    async def _process_signal_for_follower(
        self,
        follower_id: str,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
    ) -> Dict[str, Any]:
        """Process a trading signal for a specific follower.

        Args:
            follower_id: Follower ID
            strategy: Strategy type ("Long" for Bull Put, "Short" for Bear Call)
            qty_per_leg: Quantity per leg
            strike_long: Strike price for long leg
            strike_short: Strike price for short leg

        Returns:
            Dict with processing results
        """
        try:
            # Check margin
            has_margin, margin_error = await self.service.ibkr_manager.check_margin_for_trade(
                follower_id=follower_id,
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )
            
            if not has_margin:
                logger.error(
                    f"Insufficient margin for follower {follower_id}: {margin_error}"
                )
                
                # Create alert
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.NO_MARGIN,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Insufficient margin for follower {follower_id}: {margin_error}",
                )
                
                return {
                    "success": False,
                    "error": f"Insufficient margin: {margin_error}",
                }
            
            # Place vertical spread
            result = await self.service.ibkr_manager.place_vertical_spread(
                follower_id=follower_id,
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
            )
            
            # Check result
            if result["status"] == "REJECTED":
                logger.error(
                    f"Order rejected for follower {follower_id}: {result.get('error')}"
                )
                
                # Check if mid price is too low
                if result.get("mid_price") and abs(result.get("mid_price", 0)) < self.service.settings.min_price:
                    # Create alert
                    await self.service.alert_manager.create_alert(
                        follower_id=follower_id,
                        alert_type=AlertType.MID_TOO_LOW,
                        severity=AlertSeverity.CRITICAL,
                        message=f"Mid price too low for follower {follower_id}: {result.get('mid_price')}",
                    )
                else:
                    # Create alert
                    await self.service.alert_manager.create_alert(
                        follower_id=follower_id,
                        alert_type=AlertType.LIMIT_REACHED,
                        severity=AlertSeverity.CRITICAL,
                        message=f"Order rejected for follower {follower_id}: {result.get('error')}",
                    )
                
                return {
                    "success": False,
                    "error": result.get("error", "Order rejected"),
                }
            
            # Create trade record
            trade_id = str(uuid.uuid4())
            trade = Trade(
                id=trade_id,
                follower_id=follower_id,
                side=TradeSide.LONG if strategy == "Long" else TradeSide.SHORT,
                qty=qty_per_leg,
                strike=strike_long if strategy == "Long" else strike_short,
                limit_price_requested=result.get("limit_price", 0),
                status=TradeStatus(result["status"]),
                timestamps={
                    "submitted": datetime.datetime.now(),
                    "filled": datetime.datetime.now() if result["status"] == "FILLED" else None,
                },
            )
            
            # Save trade to Firestore
            self.service.db.collection("trades").document(trade_id).set(trade.to_dict())
            
            # Update position
            await self.service.position_manager.update_position(
                follower_id=follower_id,
                trade=trade,
            )
            
            # Check if partially filled
            if result["status"] == "PARTIAL":
                # Create alert
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.PARTIAL_FILL_HIGH,
                    severity=AlertSeverity.WARNING,
                    message=f"Order partially filled for follower {follower_id}: {result.get('filled', 0)}/{qty_per_leg}",
                )
            
            logger.info(
                "Processed signal for follower",
                follower_id=follower_id,
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
                status=result["status"],
            )
            
            return {
                "success": True,
                "trade_id": trade_id,
                "status": result["status"],
                "filled": result.get("filled", qty_per_leg),
                "fill_price": result.get("fill_price", 0),
            }
        except Exception as e:
            logger.error(
                f"Error processing signal for follower {follower_id}: {e}",
                exc_info=True,
            )
            
            return {
                "success": False,
                "error": str(e),
            }