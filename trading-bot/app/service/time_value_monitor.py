"""Time value monitor for SpreadPilot trading service."""

import asyncio
import datetime
from typing import Dict, Any, Optional
from enum import Enum

from spreadpilot_core.logging import get_logger
from spreadpilot_core.models import AlertType, AlertSeverity

logger = get_logger(__name__)


class RiskStatus(str, Enum):
    """Risk status levels for time value monitoring."""
    SAFE = "SAFE"
    RISK = "RISK"
    CRITICAL = "CRITICAL"


class TimeValueMonitor:
    """Monitor for time value tracking and automatic liquidation."""

    def __init__(self, service):
        """Initialize the time value monitor.

        Args:
            service: Trading service instance
        """
        self.service = service
        self.risk_statuses: Dict[str, RiskStatus] = {}
        self.monitoring_active = False
        
        logger.info("Initialized time value monitor")

    async def start_monitoring(self, shutdown_event: asyncio.Event):
        """Start time value monitoring loop.

        Args:
            shutdown_event: Event to signal shutdown
        """
        try:
            logger.info("Starting time value monitoring task")
            self.monitoring_active = True
            
            while not shutdown_event.is_set() and self.monitoring_active:
                try:
                    # Check if market is open
                    if self.service.is_market_open():
                        # Monitor time value for all active followers
                        for follower_id in self.service.active_followers:
                            await self.monitor_time_value(follower_id)
                    
                    # Wait 60 seconds before next check
                    await asyncio.sleep(60)
                
                except Exception as e:
                    logger.error(f"Error in time value monitoring: {e}", exc_info=True)
                    await asyncio.sleep(10)  # Wait before retrying
            
            logger.info("Time value monitoring task stopped")
        
        except asyncio.CancelledError:
            logger.info("Time value monitoring task cancelled")
            self.monitoring_active = False
            raise
        
        except Exception as e:
            logger.error(f"Error in time value monitoring task: {e}", exc_info=True)
            self.monitoring_active = False

    async def monitor_time_value(self, follower_id: str):
        """Monitor time value for a specific follower.

        Args:
            follower_id: Follower ID to monitor
        """
        try:
            # Get IBKR client
            client = await self.service.ibkr_manager.get_client(follower_id)
            if not client:
                logger.error(f"Failed to get IBKR client for follower {follower_id}")
                return

            # Get current positions
            positions = await client.get_positions(force_update=True)
            if not positions:
                # No positions, set status to SAFE
                await self._update_risk_status(follower_id, RiskStatus.SAFE)
                return

            # Calculate time value for spread positions
            time_value = await self._calculate_time_value(client, positions)
            
            if time_value is None:
                logger.warning(f"Could not calculate time value for follower {follower_id}")
                return

            logger.debug(f"Time value for follower {follower_id}: ${time_value:.4f}")

            # Determine risk status and take action
            if time_value < 0.10:
                # CRITICAL: Liquidate positions
                await self._handle_critical_time_value(follower_id, time_value)
            elif time_value < 0.20:  # Risk threshold
                # RISK: Monitor closely
                await self._update_risk_status(follower_id, RiskStatus.RISK)
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.RISK_WARNING,
                    severity=AlertSeverity.WARNING,
                    message=f"Time value approaching liquidation threshold: ${time_value:.4f}",
                )
            else:
                # SAFE: Normal operation
                await self._update_risk_status(follower_id, RiskStatus.SAFE)

        except Exception as e:
            logger.error(f"Error monitoring time value for follower {follower_id}: {e}")

    async def _calculate_time_value(self, client, positions: Dict[str, int]) -> Optional[float]:
        """Calculate time value for spread positions.

        Args:
            client: IBKR client instance
            positions: Position dictionary from client

        Returns:
            Time value or None if calculation fails
        """
        try:
            # Get market data for spread
            spread_mark_price = await client.get_spread_mark_price()
            if spread_mark_price is None:
                logger.warning("Could not get spread mark price")
                return None

            # Calculate intrinsic value
            intrinsic_value = await self._calculate_intrinsic_value(client, positions)
            if intrinsic_value is None:
                logger.warning("Could not calculate intrinsic value")
                return None

            # Time value = spread_mark_price - intrinsic_value
            time_value = spread_mark_price - intrinsic_value
            
            return max(0.0, time_value)  # Time value cannot be negative

        except Exception as e:
            logger.error(f"Error calculating time value: {e}")
            return None

    async def _calculate_intrinsic_value(self, client, positions: Dict[str, int]) -> Optional[float]:
        """Calculate intrinsic value of the spread.

        Args:
            client: IBKR client instance
            positions: Position dictionary from client

        Returns:
            Intrinsic value or None if calculation fails
        """
        try:
            # Get current underlying price (QQQ)
            underlying_price = await client.get_underlying_price("QQQ")
            if underlying_price is None:
                logger.warning("Could not get underlying price for QQQ")
                return None

            intrinsic_value = 0.0

            # Calculate intrinsic value for each position
            for position_key, qty in positions.items():
                if qty == 0:
                    continue

                # Parse position key (format: "strike-right")
                try:
                    strike_str, right = position_key.split("-")
                    strike = float(strike_str)
                except ValueError:
                    logger.warning(f"Could not parse position key: {position_key}")
                    continue

                # Calculate intrinsic value per contract
                if right.upper() == "CALL":
                    contract_intrinsic = max(0, underlying_price - strike)
                elif right.upper() == "PUT":
                    contract_intrinsic = max(0, strike - underlying_price)
                else:
                    logger.warning(f"Unknown option type: {right}")
                    continue

                # Add to total intrinsic value (considering position quantity and sign)
                intrinsic_value += contract_intrinsic * abs(qty) * (1 if qty > 0 else -1)

            return intrinsic_value

        except Exception as e:
            logger.error(f"Error calculating intrinsic value: {e}")
            return None

    async def _handle_critical_time_value(self, follower_id: str, time_value: float):
        """Handle critical time value by liquidating positions.

        Args:
            follower_id: Follower ID
            time_value: Current time value
        """
        try:
            # Update status to CRITICAL
            await self._update_risk_status(follower_id, RiskStatus.CRITICAL)

            # Create critical alert
            await self.service.alert_manager.create_alert(
                follower_id=follower_id,
                alert_type=AlertType.TIME_VALUE_CRITICAL,
                severity=AlertSeverity.CRITICAL,
                message=f"Time value critical (${time_value:.4f}), initiating liquidation",
            )

            logger.warning(
                "Time value critical, liquidating positions",
                follower_id=follower_id,
                time_value=time_value,
            )

            # Execute market order to close all positions
            result = await self.service.position_manager.close_positions(follower_id)

            if result["success"]:
                logger.info(
                    "Successfully liquidated positions due to time value",
                    follower_id=follower_id,
                    time_value=time_value,
                )

                # Create success alert
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.LIQUIDATION_COMPLETE,
                    severity=AlertSeverity.INFO,
                    message=f"Positions liquidated due to time value: ${time_value:.4f}",
                )

                # Update status back to SAFE after successful liquidation
                await self._update_risk_status(follower_id, RiskStatus.SAFE)

            else:
                logger.error(
                    f"Failed to liquidate positions: {result.get('error')}",
                    follower_id=follower_id,
                )

                # Create failure alert
                await self.service.alert_manager.create_alert(
                    follower_id=follower_id,
                    alert_type=AlertType.LIQUIDATION_FAILED,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Failed to liquidate positions: {result.get('error')}",
                )

        except Exception as e:
            logger.error(f"Error handling critical time value for follower {follower_id}: {e}")

    async def _update_risk_status(self, follower_id: str, status: RiskStatus):
        """Update risk status in Redis and local cache.

        Args:
            follower_id: Follower ID
            status: New risk status
        """
        try:
            # Update local cache
            self.risk_statuses[follower_id] = status

            # Update Redis if available
            if hasattr(self.service, 'redis_client') and self.service.redis_client:
                key = f"risk_status:{follower_id}"
                await self.service.redis_client.set(key, status.value, ex=300)  # 5-minute expiry
                
                # Also publish status change
                await self.service.redis_client.publish(
                    "risk_status_updates",
                    f"{follower_id}:{status.value}:{datetime.datetime.now().isoformat()}"
                )

            logger.debug(f"Updated risk status for {follower_id}: {status.value}")

        except Exception as e:
            logger.error(f"Error updating risk status for follower {follower_id}: {e}")

    async def get_risk_status(self, follower_id: str) -> RiskStatus:
        """Get current risk status for a follower.

        Args:
            follower_id: Follower ID

        Returns:
            Current risk status
        """
        try:
            # Try Redis first if available
            if hasattr(self.service, 'redis_client') and self.service.redis_client:
                key = f"risk_status:{follower_id}"
                status_str = await self.service.redis_client.get(key)
                if status_str:
                    return RiskStatus(status_str.decode() if isinstance(status_str, bytes) else status_str)

            # Fall back to local cache
            return self.risk_statuses.get(follower_id, RiskStatus.SAFE)

        except Exception as e:
            logger.error(f"Error getting risk status for follower {follower_id}: {e}")
            return RiskStatus.SAFE

    async def get_all_risk_statuses(self) -> Dict[str, RiskStatus]:
        """Get risk statuses for all followers.

        Returns:
            Dictionary of follower_id -> risk_status
        """
        statuses = {}
        
        for follower_id in self.service.active_followers:
            statuses[follower_id] = await self.get_risk_status(follower_id)
        
        return statuses

    async def stop_monitoring(self):
        """Stop the time value monitoring."""
        logger.info("Stopping time value monitoring")
        self.monitoring_active = False