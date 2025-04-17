"""Position manager for SpreadPilot trading service."""

import asyncio
import datetime
from typing import Dict, Any

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import (
    AlertType,
    AlertSeverity,
    AssignmentState,
    Position,
    Trade,
)
from spreadpilot_core.utils.time import get_current_trading_date

logger = get_logger(__name__)


class PositionManager:
    """Manager for position tracking and assignment handling."""

    def __init__(self, service):
        """Initialize the position manager.

        Args:
            service: Trading service instance
        """
        self.service = service
        self.positions: Dict[str, Position] = {}
        
        logger.info("Initialized position manager")

    async def update_position(self, follower_id: str, trade: Trade):
        """Update position for a follower.

        Args:
            follower_id: Follower ID
            trade: Trade record
        """
        try:
            # Get current trading date
            trading_date = get_current_trading_date()
            
            # Get position document
            position_ref = self.service.db.collection("positions").document(follower_id).collection("daily").document(trading_date)
            position_doc = position_ref.get()
            
            # Create position if it doesn't exist
            if not position_doc.exists:
                position = Position(
                    follower_id=follower_id,
                    date=trading_date,
                    short_qty=0,
                    long_qty=0,
                    pnl_realized=0.0,
                    pnl_mtm=0.0,
                    assignment_state=AssignmentState.NONE,
                )
            else:
                # Get existing position
                position = Position.from_dict(
                    follower_id=follower_id,
                    date=trading_date,
                    data=position_doc.to_dict(),
                )
            
            # Update position based on trade
            if trade.side == "LONG":
                position.long_qty += trade.qty
            else:
                position.short_qty += trade.qty
            
            # Update timestamp
            position.updated_at = datetime.datetime.now()
            
            # Save position
            position_ref.set(position.to_dict())
            
            # Update cache
            self.positions[follower_id] = position
            
            logger.info(
                "Updated position",
                follower_id=follower_id,
                date=trading_date,
                long_qty=position.long_qty,
                short_qty=position.short_qty,
            )
        except Exception as e:
            logger.error(f"Error updating position for follower {follower_id}: {e}")

    async def check_positions_periodically(self, shutdown_event: asyncio.Event):
        """Check positions periodically for assignments.

        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting position check task")
            
            while not shutdown_event.is_set():
                try:
                    # Check if market is open
                    if self.service.is_market_open():
                        # Check positions for all active followers
                        for follower_id in self.service.active_followers:
                            await self.check_positions(follower_id)
                    
                    # Wait for next check
                    await asyncio.sleep(self.service.settings.position_check_interval_seconds)
                
                except Exception as e:
                    logger.error(f"Error checking positions: {e}", exc_info=True)
                    await asyncio.sleep(10)  # Wait before retrying
            
            logger.info("Position check task stopped")
        
        except asyncio.CancelledError:
            logger.info("Position check task cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Error in position check task: {e}", exc_info=True)

    async def check_positions(self, follower_id: str):
        """Check positions for a follower.

        Args:
            follower_id: Follower ID
        """
        try:
            # Get IBKR client
            client = await self.service.ibkr_manager.get_client(follower_id)
            if not client:
                logger.error(f"Failed to get IBKR client for follower {follower_id}")
                return
            
            # Check for assignment
            assignment_state, short_qty, long_qty = await client.check_assignment()
            
            # Get current trading date
            trading_date = get_current_trading_date()
            
            # Get position document
            position_ref = self.service.db.collection("positions").document(follower_id).collection("daily").document(trading_date)
            position_doc = position_ref.get()
            
            # Create position if it doesn't exist
            if not position_doc.exists:
                position = Position(
                    follower_id=follower_id,
                    date=trading_date,
                    short_qty=short_qty,
                    long_qty=long_qty,
                    pnl_realized=0.0,
                    pnl_mtm=0.0,
                    assignment_state=assignment_state,
                )
            else:
                # Get existing position
                position = Position.from_dict(
                    follower_id=follower_id,
                    date=trading_date,
                    data=position_doc.to_dict(),
                )
                
                # Update quantities
                position.short_qty = short_qty
                position.long_qty = long_qty
            
            # Check for assignment
            if assignment_state == AssignmentState.ASSIGNED:
                # Calculate missing short positions
                missing_short_qty = long_qty - short_qty
                
                logger.warning(
                    "Assignment detected",
                    follower_id=follower_id,
                    short_qty=short_qty,
                    long_qty=long_qty,
                    missing_short_qty=missing_short_qty,
                )
                
                # Create alert
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.ASSIGNMENT_DETECTED,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Assignment detected for follower {follower_id}: {missing_short_qty} positions",
                )
                
                # Update position state
                position.assignment_state = AssignmentState.ASSIGNED
                
                # Save position
                position_ref.set(position.to_dict())
                
                # Update cache
                self.positions[follower_id] = position
                
                # Exercise long options to compensate
                # Note: This is a simplified implementation, in a real system we would need to
                # determine the correct strike price for the long options to exercise
                if missing_short_qty > 0:
                    # Get position details from IBKR to determine which long options to exercise
                    positions = await client.get_positions(force_update=True)
                    
                    # Find long positions
                    long_positions = {}
                    for key, qty in positions.items():
                        if qty > 0:  # Long position
                            strike, right = key.split("-")
                            long_positions[key] = {
                                "strike": float(strike),
                                "right": right,
                                "qty": qty,
                            }
                    
                    if long_positions:
                        # Exercise the first long position we find
                        # In a real system, we would need to be more selective
                        key, pos = next(iter(long_positions.items()))
                        
                        logger.info(
                            "Exercising long options",
                            follower_id=follower_id,
                            strike=pos["strike"],
                            right=pos["right"],
                            qty=min(missing_short_qty, pos["qty"]),
                        )
                        
                        # Exercise options
                        result = await self.service.ibkr_manager.exercise_options(
                            follower_id=follower_id,
                            strike=pos["strike"],
                            right=pos["right"],
                            quantity=min(missing_short_qty, pos["qty"]),
                        )
                        
                        if result["success"]:
                            # Update position state
                            position.assignment_state = AssignmentState.COMPENSATED
                            
                            # Save position
                            position_ref.set(position.to_dict())
                            
                            # Update cache
                            self.positions[follower_id] = position
                            
                            # Create alert
                            await self.service.alert_manager.create_alert(
                                follower_id=follower_id,
                                alert_type=AlertType.ASSIGNMENT_COMPENSATED,
                                severity=AlertSeverity.INFO,
                                message=f"Assignment compensated for follower {follower_id}: exercised {min(missing_short_qty, pos['qty'])} options",
                            )
                        else:
                            logger.error(
                                f"Failed to exercise options: {result.get('error')}",
                                follower_id=follower_id,
                            )
                    else:
                        logger.error(
                            "No long positions found to exercise",
                            follower_id=follower_id,
                        )
            
            # Update P&L
            pnl = await client.get_pnl()
            if pnl:
                position.pnl_realized = pnl.get("realized_pnl", 0.0)
                position.pnl_mtm = pnl.get("unrealized_pnl", 0.0)
                
                # Save position
                position_ref.set(position.to_dict())
                
                # Update cache
                self.positions[follower_id] = position
            
            logger.debug(
                "Checked positions",
                follower_id=follower_id,
                short_qty=short_qty,
                long_qty=long_qty,
                assignment_state=assignment_state,
                pnl_realized=position.pnl_realized,
                pnl_mtm=position.pnl_mtm,
            )
        
        except Exception as e:
            logger.error(f"Error checking positions for follower {follower_id}: {e}")

    async def close_positions(self, follower_id: str) -> Dict[str, Any]:
        """Close all positions for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Dict with results
        """
        try:
            # Check if follower is active
            if follower_id not in self.service.active_followers:
                logger.error(f"Follower not found or not active: {follower_id}")
                return {
                    "success": False,
                    "error": f"Follower not found or not active: {follower_id}",
                }
            
            # Close positions
            result = await self.service.ibkr_manager.close_positions(follower_id)
            
            # Log result
            if result["success"]:
                logger.info(
                    "Closed positions for follower",
                    follower_id=follower_id,
                    results=result["results"],
                )
            else:
                logger.error(
                    f"Failed to close positions for follower {follower_id}: {result.get('error')}",
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Error closing positions for follower {follower_id}: {e}")
            
            return {
                "success": False,
                "error": str(e),
            }

    async def close_all_positions(self) -> Dict[str, Any]:
        """Close all positions for all followers.

        Returns:
            Dict with results
        """
        results = {}
        success = True
        
        # Close positions for each follower
        for follower_id in self.service.active_followers:
            result = await self.close_positions(follower_id)
            results[follower_id] = result
            
            # Update overall success
            if not result["success"]:
                success = False
        
        return {
            "success": success,
            "results": results,
        }