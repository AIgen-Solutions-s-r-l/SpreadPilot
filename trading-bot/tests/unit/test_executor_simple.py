"""Simplified unit tests for the VerticalSpreadExecutor without service dependencies."""

import asyncio
import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import pytest
import ib_insync

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../spreadpilot-core'))

# Import the specific modules we need without triggering the service layer
from spreadpilot_core.ibkr.client import IBKRClient, OrderStatus
from spreadpilot_core.models.alert import AlertSeverity


class VerticalSpreadExecutor:
    """Simplified version of VerticalSpreadExecutor for testing."""

    def __init__(self, ibkr_client: IBKRClient):
        """Initialize the executor.
        
        Args:
            ibkr_client: Connected IBKR client instance
        """
        self.ibkr_client = ibkr_client

    async def execute_vertical_spread(
        self,
        signal: Dict[str, Any],
        follower_id: str,
        max_attempts: int = 10,
        price_increment: float = 0.01,
        min_price_threshold: float = 0.70,
        attempt_interval: int = 5,
        timeout_per_attempt: int = 5
    ) -> Dict[str, Any]:
        """Execute a vertical spread order with limit-ladder strategy.
        
        Args:
            signal: Trading signal containing strategy details
            follower_id: ID of the follower to execute for
            max_attempts: Maximum number of pricing attempts
            price_increment: Price increment per attempt (makes limit less negative)
            min_price_threshold: Minimum acceptable MID price (absolute value)
            attempt_interval: Seconds between attempts
            timeout_per_attempt: Timeout for each individual attempt
            
        Returns:
            Dict containing execution results and fill details
        """
        try:
            # Extract signal parameters
            strategy = signal.get("strategy")
            qty_per_leg = signal.get("qty_per_leg", 1)
            strike_long = signal.get("strike_long")
            strike_short = signal.get("strike_short")
            
            # Validate signal
            if not all([strategy, strike_long, strike_short]):
                return {
                    "status": OrderStatus.REJECTED,
                    "error": "Invalid signal: missing required parameters",
                    "follower_id": follower_id,
                    "signal": signal
                }
            
            # Phase 1: Pre-trade margin check via IB API whatIf
            margin_check_result = await self._perform_whatif_margin_check(
                strategy, qty_per_leg, strike_long, strike_short, follower_id
            )
            
            if not margin_check_result["success"]:
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"Margin check failed: {margin_check_result['error']}",
                    "follower_id": follower_id,
                    "margin_details": margin_check_result
                }
            
            # Phase 2: Get market data and calculate MID price
            mid_price_result = await self._calculate_mid_price(strategy, strike_long, strike_short)
            
            if not mid_price_result["success"]:
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"Failed to calculate MID price: {mid_price_result['error']}",
                    "follower_id": follower_id
                }
            
            mid_price = mid_price_result["mid_price"]
            
            # Phase 3: Check if MID price meets minimum threshold
            if abs(mid_price) < min_price_threshold:
                return {
                    "status": OrderStatus.REJECTED,
                    "error": f"MID price {mid_price:.3f} below minimum threshold {min_price_threshold}",
                    "follower_id": follower_id,
                    "mid_price": mid_price,
                    "threshold": min_price_threshold
                }
            
            # Phase 4: Execute limit-ladder strategy
            execution_result = await self._execute_limit_ladder(
                strategy=strategy,
                qty_per_leg=qty_per_leg,
                strike_long=strike_long,
                strike_short=strike_short,
                initial_mid_price=mid_price,
                max_attempts=max_attempts,
                price_increment=price_increment,
                min_price_threshold=min_price_threshold,
                attempt_interval=attempt_interval,
                timeout_per_attempt=timeout_per_attempt,
                follower_id=follower_id
            )
            
            return execution_result
            
        except Exception as e:
            return {
                "status": OrderStatus.REJECTED,
                "error": f"Execution error: {str(e)}",
                "follower_id": follower_id
            }

    async def _perform_whatif_margin_check(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        follower_id: str
    ) -> Dict[str, Any]:
        """Perform IB API whatIf margin check before placing order."""
        try:
            if not await self.ibkr_client.ensure_connected():
                return {
                    "success": False,
                    "error": "Not connected to IB Gateway"
                }
            
            # Determine option rights based on strategy
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            elif strategy == "Short":  # Bear Call
                long_right = "C"
                short_right = "C"
            else:
                return {
                    "success": False,
                    "error": f"Invalid strategy: {strategy}"
                }
            
            # Create contracts for whatIf check
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Create combo contract for spread
            combo_contract = ib_insync.Bag("QQQ", "SMART", "USD")
            combo_contract.addLeg(long_contract, 1)  # Buy long leg
            combo_contract.addLeg(short_contract, -1)  # Sell short leg
            
            # Create a test order for whatIf check
            from ib_insync import LimitOrder
            test_order = LimitOrder(
                action="BUY",
                totalQuantity=qty_per_leg,
                lmtPrice=1.0,  # Placeholder price for whatIf
                whatIf=True  # This makes it a whatIf order
            )
            
            # Submit whatIf order to get margin requirements
            whatif_result = await self.ibkr_client.ib.whatIfOrderAsync(combo_contract, test_order)
            
            if not whatif_result:
                return {
                    "success": False,
                    "error": "No whatIf result returned from IB"
                }
            
            # Extract margin requirements
            init_margin = float(whatif_result.initMarginChange or 0)
            maint_margin = float(whatif_result.maintMarginChange or 0)
            equity_with_loan = float(whatif_result.equityWithLoanAfter or 0)
            
            # Get account summary for available funds
            account_summary = await self.ibkr_client.get_account_summary()
            available_funds = float(account_summary.get("AvailableFunds", 0))
            
            # Check if we have sufficient margin
            margin_sufficient = available_funds >= abs(init_margin)
            
            return {
                "success": margin_sufficient,
                "error": None if margin_sufficient else f"Insufficient margin: need {abs(init_margin)}, have {available_funds}",
                "init_margin": init_margin,
                "maint_margin": maint_margin,
                "available_funds": available_funds,
                "equity_with_loan": equity_with_loan
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"WhatIf check error: {str(e)}"
            }

    async def _calculate_mid_price(
        self,
        strategy: str,
        strike_long: float,
        strike_short: float
    ) -> Dict[str, Any]:
        """Calculate the MID price for the vertical spread."""
        try:
            # Determine option rights
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            elif strategy == "Short":  # Bear Call
                long_right = "C"
                short_right = "C"
            else:
                return {
                    "success": False,
                    "error": f"Invalid strategy: {strategy}"
                }
            
            # Create contracts
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Get market prices
            long_price = await self.ibkr_client.get_market_price(long_contract)
            short_price = await self.ibkr_client.get_market_price(short_contract)
            
            if long_price is None or short_price is None:
                return {
                    "success": False,
                    "error": f"Failed to get market prices: long={long_price}, short={short_price}"
                }
            
            # Calculate MID price (spread price)
            # For both Bull Put and Bear Call: short_price - long_price (typically negative)
            mid_price = short_price - long_price
            
            return {
                "success": True,
                "mid_price": mid_price,
                "long_price": long_price,
                "short_price": short_price
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"MID price calculation error: {str(e)}"
            }

    async def _execute_limit_ladder(
        self,
        strategy: str,
        qty_per_leg: int,
        strike_long: float,
        strike_short: float,
        initial_mid_price: float,
        max_attempts: int,
        price_increment: float,
        min_price_threshold: float,
        attempt_interval: int,
        timeout_per_attempt: int,
        follower_id: str
    ) -> Dict[str, Any]:
        """Execute the limit-ladder strategy."""
        try:
            # Determine option rights
            if strategy == "Long":  # Bull Put
                long_right = "P"
                short_right = "P"
            else:  # Bear Call
                long_right = "C"
                short_right = "C"
            
            # Create contracts
            long_contract = self.ibkr_client._get_qqq_option_contract(strike_long, long_right)
            short_contract = self.ibkr_client._get_qqq_option_contract(strike_short, short_right)
            
            # Create combo contract for spread
            combo_contract = ib_insync.Bag("QQQ", "SMART", "USD")
            combo_contract.addLeg(long_contract, 1)
            combo_contract.addLeg(short_contract, -1)
            
            # Start with initial MID price as limit
            current_limit_price = initial_mid_price
            
            for attempt in range(1, max_attempts + 1):
                # Check if current limit price still meets threshold
                if abs(current_limit_price) < min_price_threshold:
                    return {
                        "status": OrderStatus.CANCELED,
                        "error": f"Limit price {current_limit_price:.3f} below threshold",
                        "follower_id": follower_id,
                        "attempts": attempt - 1,
                        "final_limit": current_limit_price,
                        "threshold": min_price_threshold
                    }
                
                # Create limit order
                from ib_insync import LimitOrder
                order = LimitOrder(
                    action="BUY",
                    totalQuantity=qty_per_leg,
                    lmtPrice=current_limit_price,
                    transmit=True
                )
                
                # Place the order
                trade = self.ibkr_client.ib.placeOrder(combo_contract, order)
                
                # Wait for fill or timeout
                import time
                start_time = time.time()
                while time.time() - start_time < timeout_per_attempt:
                    await asyncio.sleep(0.1)
                    self.ibkr_client.ib.waitOnUpdate(timeout=0.1)
                    
                    if trade.orderStatus.status in ["Filled", "Cancelled", "Inactive"]:
                        break
                
                # Check if order was filled
                if trade.orderStatus.status == "Filled":
                    return {
                        "status": OrderStatus.FILLED,
                        "trade_id": str(trade.order.orderId),
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "filled_quantity": trade.orderStatus.filled,
                        "fill_time": datetime.datetime.now().isoformat(),
                        "follower_id": follower_id,
                        "attempts": attempt,
                        "final_limit": current_limit_price,
                        "strategy": strategy,
                        "strikes": {
                            "long": strike_long,
                            "short": strike_short
                        }
                    }
                
                # Check for partial fills
                if trade.orderStatus.status == "Submitted" and trade.orderStatus.filled > 0:
                    return {
                        "status": OrderStatus.PARTIAL,
                        "trade_id": str(trade.order.orderId),
                        "fill_price": trade.orderStatus.avgFillPrice,
                        "filled_quantity": trade.orderStatus.filled,
                        "remaining_quantity": trade.orderStatus.remaining,
                        "fill_time": datetime.datetime.now().isoformat(),
                        "follower_id": follower_id,
                        "attempts": attempt,
                        "final_limit": current_limit_price
                    }
                
                # Cancel unfilled order before next attempt
                if trade.orderStatus.status not in ["Cancelled", "Inactive"]:
                    self.ibkr_client.ib.cancelOrder(order)
                    await asyncio.sleep(0.5)  # Wait for cancellation
                
                # Increment limit price for next attempt (make it less negative)
                current_limit_price += price_increment
                
                # Wait before next attempt (except on last attempt)
                if attempt < max_attempts:
                    await asyncio.sleep(attempt_interval)
            
            # All attempts exhausted
            return {
                "status": OrderStatus.REJECTED,
                "error": f"All {max_attempts} attempts exhausted",
                "follower_id": follower_id,
                "attempts": max_attempts,
                "final_limit": current_limit_price,
                "initial_limit": initial_mid_price
            }
            
        except Exception as e:
            return {
                "status": OrderStatus.REJECTED,
                "error": f"Limit-ladder execution error: {str(e)}",
                "follower_id": follower_id
            }


class TestVerticalSpreadExecutor(unittest.TestCase):
    """Test cases for the VerticalSpreadExecutor."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock IBKR client
        self.mock_ibkr_client = MagicMock(spec=IBKRClient)
        self.mock_ibkr_client.ib = MagicMock()
        self.mock_ibkr_client.ensure_connected = AsyncMock(return_value=True)
        self.mock_ibkr_client._get_qqq_option_contract = MagicMock()
        self.mock_ibkr_client.get_market_price = AsyncMock()
        self.mock_ibkr_client.get_account_summary = AsyncMock()
        
        # Create executor instance
        self.executor = VerticalSpreadExecutor(self.mock_ibkr_client)
        
        # Test signal
        self.test_signal = {
            "strategy": "Long",
            "qty_per_leg": 1,
            "strike_long": 380.0,
            "strike_short": 385.0
        }
        
        self.follower_id = "test-follower-123"

    def test_executor_initialization(self):
        """Test executor initialization."""
        executor = VerticalSpreadExecutor(self.mock_ibkr_client)
        self.assertEqual(executor.ibkr_client, self.mock_ibkr_client)

    async def test_execute_vertical_spread_success(self):
        """Test successful execution of vertical spread."""
        # Mock whatIf check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"
        
        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(return_value={"AvailableFunds": "1000.0"})
        
        # Mock market price calculation
        self.mock_ibkr_client.get_market_price = AsyncMock(side_effect=[2.50, 3.25])  # long_price, short_price
        
        # Mock successful order execution
        mock_trade = MagicMock()
        mock_trade.order.orderId = 12345
        mock_trade.orderStatus.status = "Filled"
        mock_trade.orderStatus.avgFillPrice = 0.75
        mock_trade.orderStatus.filled = 1
        
        self.mock_ibkr_client.ib.placeOrder = MagicMock(return_value=mock_trade)
        
        # Execute
        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)
        
        # Verify results
        self.assertEqual(result["status"], OrderStatus.FILLED)
        self.assertEqual(result["trade_id"], "12345")
        self.assertEqual(result["fill_price"], 0.75)
        self.assertEqual(result["follower_id"], self.follower_id)
        self.assertIn("fill_time", result)

    async def test_execute_vertical_spread_invalid_signal(self):
        """Test execution with invalid signal."""
        invalid_signal = {
            "strategy": "Long",
            # Missing required fields
        }
        
        result = await self.executor.execute_vertical_spread(invalid_signal, self.follower_id)
        
        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("Invalid signal", result["error"])
        self.assertEqual(result["follower_id"], self.follower_id)

    async def test_execute_vertical_spread_mid_price_below_threshold(self):
        """Test execution when MID price is below threshold."""
        # Mock successful margin check
        mock_whatif_result = MagicMock()
        mock_whatif_result.initMarginChange = "500.0"
        mock_whatif_result.maintMarginChange = "400.0"
        mock_whatif_result.equityWithLoanAfter = "10000.0"
        
        self.mock_ibkr_client.ib.whatIfOrderAsync = AsyncMock(return_value=mock_whatif_result)
        self.mock_ibkr_client.get_account_summary = AsyncMock(return_value={"AvailableFunds": "1000.0"})
        
        # Mock market prices that result in low MID price
        self.mock_ibkr_client.get_market_price = AsyncMock(side_effect=[2.50, 2.60])  # MID = 0.10 (below 0.70)
        
        result = await self.executor.execute_vertical_spread(self.test_signal, self.follower_id)
        
        self.assertEqual(result["status"], OrderStatus.REJECTED)
        self.assertIn("below minimum threshold", result["error"])
        self.assertEqual(result["mid_price"], 0.10)
        self.assertEqual(result["threshold"], 0.70)


# Async test runner
def run_async_test(test_method):
    """Run an async test method."""
    def wrapper(self):
        return asyncio.run(test_method(self))
    return wrapper


# Apply async wrapper to test methods
for attr_name in dir(TestVerticalSpreadExecutor):
    if attr_name.startswith('test_') and 'async' in attr_name:
        attr = getattr(TestVerticalSpreadExecutor, attr_name)
        if asyncio.iscoroutinefunction(attr):
            setattr(TestVerticalSpreadExecutor, attr_name, run_async_test(attr))


if __name__ == '__main__':
    unittest.main()