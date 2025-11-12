"""Unit tests for QQQ signal generator."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from ib_insync import IB

# Import from trading_bot package
import sys
from pathlib import Path

# Add trading-bot directory to path
trading_bot_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(trading_bot_dir))

from app.signal_generator import QQQSignalGenerator


@pytest.fixture
def mock_ib_client():
    """Create a mock IBKR client."""
    client = Mock(spec=IB)
    client.qualifyContracts = Mock(return_value=[])
    client.reqMktData = Mock()
    client.cancelMktData = Mock()
    client.reqHistoricalData = Mock()
    client.reqSecDefOptParams = Mock()
    return client


@pytest.fixture
def signal_generator(mock_ib_client):
    """Create a signal generator instance."""
    return QQQSignalGenerator(
        ib_client=mock_ib_client,
        short_leg_delta=0.30,
        long_leg_delta=0.15,
        sma_short_period=20,
        sma_long_period=50,
        qty_per_leg=1,
    )


class TestQQQSignalGeneratorInit:
    """Test signal generator initialization."""

    def test_initialization_with_defaults(self, mock_ib_client):
        """Test initialization with default parameters."""
        generator = QQQSignalGenerator(ib_client=mock_ib_client)

        assert generator.ib == mock_ib_client
        assert generator.short_leg_delta == 0.30
        assert generator.long_leg_delta == 0.15
        assert generator.sma_short_period == 20
        assert generator.sma_long_period == 50
        assert generator.qty_per_leg == 1
        assert generator._price_cache == []
        assert generator._cache_updated is None

    def test_initialization_with_custom_params(self, mock_ib_client):
        """Test initialization with custom parameters."""
        generator = QQQSignalGenerator(
            ib_client=mock_ib_client,
            short_leg_delta=0.25,
            long_leg_delta=0.10,
            sma_short_period=10,
            sma_long_period=30,
            qty_per_leg=2,
        )

        assert generator.short_leg_delta == 0.25
        assert generator.long_leg_delta == 0.10
        assert generator.sma_short_period == 10
        assert generator.sma_long_period == 30
        assert generator.qty_per_leg == 2

    def test_initialization_negative_delta_converted_to_positive(self, mock_ib_client):
        """Test that negative deltas are converted to positive."""
        generator = QQQSignalGenerator(
            ib_client=mock_ib_client,
            short_leg_delta=-0.30,
            long_leg_delta=-0.15,
        )

        assert generator.short_leg_delta == 0.30
        assert generator.long_leg_delta == 0.15


class TestGetCurrentPrice:
    """Test getting current QQQ price."""

    @pytest.mark.asyncio
    async def test_get_current_price_success(self, signal_generator, mock_ib_client):
        """Test successful price retrieval."""
        # Mock ticker with last price
        mock_ticker = Mock()
        mock_ticker.last = 450.25
        mock_ticker.close = 449.50
        mock_ib_client.reqMktData.return_value = mock_ticker

        price = await signal_generator._get_current_price()

        assert price == 450.25
        mock_ib_client.qualifyContracts.assert_called_once()
        mock_ib_client.reqMktData.assert_called_once()
        mock_ib_client.cancelMktData.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_price_fallback_to_close(self, signal_generator, mock_ib_client):
        """Test fallback to close price when last is unavailable."""
        # Mock ticker with only close price
        mock_ticker = Mock()
        mock_ticker.last = None
        mock_ticker.close = 449.50
        mock_ib_client.reqMktData.return_value = mock_ticker

        price = await signal_generator._get_current_price()

        assert price == 449.50
        mock_ib_client.cancelMktData.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_price_no_data(self, signal_generator, mock_ib_client):
        """Test when no price data is available."""
        # Mock ticker with no data
        mock_ticker = Mock()
        mock_ticker.last = None
        mock_ticker.close = None
        mock_ib_client.reqMktData.return_value = mock_ticker

        price = await signal_generator._get_current_price()

        assert price is None
        mock_ib_client.cancelMktData.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_price_exception(self, signal_generator, mock_ib_client):
        """Test exception handling during price retrieval."""
        mock_ib_client.reqMktData.side_effect = Exception("Connection error")

        price = await signal_generator._get_current_price()

        assert price is None


class TestDetermineStrategy:
    """Test strategy determination using SMA crossover."""

    @pytest.mark.asyncio
    async def test_determine_strategy_bullish(self, signal_generator):
        """Test bullish strategy determination (SMA short > SMA long)."""
        # Set up price cache with bullish trend
        signal_generator._price_cache = [100 + i * 0.5 for i in range(50)]
        signal_generator._cache_updated = datetime.utcnow()

        strategy = await signal_generator._determine_strategy(current_price=125.0)

        assert strategy == "Long"

    @pytest.mark.asyncio
    async def test_determine_strategy_bearish(self, signal_generator):
        """Test bearish strategy determination (SMA short < SMA long)."""
        # Set up price cache with bearish trend
        signal_generator._price_cache = [150 - i * 0.5 for i in range(50)]
        signal_generator._cache_updated = datetime.utcnow()

        strategy = await signal_generator._determine_strategy(current_price=125.0)

        assert strategy == "Short"

    @pytest.mark.asyncio
    async def test_determine_strategy_neutral(self, signal_generator):
        """Test neutral strategy when SMAs are equal."""
        # Set up price cache with no clear trend
        signal_generator._price_cache = [100.0] * 50
        signal_generator._cache_updated = datetime.utcnow()

        strategy = await signal_generator._determine_strategy(current_price=100.0)

        assert strategy is None

    @pytest.mark.asyncio
    async def test_determine_strategy_insufficient_data_uses_fallback(self, signal_generator):
        """Test fallback when insufficient data for SMA calculation."""
        # Set up price cache with insufficient data
        signal_generator._price_cache = [100.0, 101.0, 102.0, 103.0, 104.0]
        signal_generator._cache_updated = datetime.utcnow()

        with patch.object(
            signal_generator, "_fallback_strategy", return_value="Long"
        ) as mock_fallback:
            strategy = await signal_generator._determine_strategy(current_price=105.0)

            assert strategy == "Long"
            mock_fallback.assert_called_once_with(105.0)

    @pytest.mark.asyncio
    async def test_determine_strategy_exception(self, signal_generator):
        """Test exception handling in strategy determination."""
        signal_generator._price_cache = None  # Force an error

        strategy = await signal_generator._determine_strategy(current_price=100.0)

        assert strategy is None


class TestFallbackStrategy:
    """Test fallback strategy using momentum."""

    @pytest.mark.asyncio
    async def test_fallback_strategy_bullish_momentum(self, signal_generator):
        """Test bullish momentum detection."""
        signal_generator._price_cache = [100.0, 101.0, 102.0, 103.0, 104.0]

        strategy = await signal_generator._fallback_strategy(current_price=106.0)

        assert strategy == "Long"

    @pytest.mark.asyncio
    async def test_fallback_strategy_bearish_momentum(self, signal_generator):
        """Test bearish momentum detection."""
        signal_generator._price_cache = [110.0, 109.0, 108.0, 107.0, 106.0]

        strategy = await signal_generator._fallback_strategy(current_price=104.0)

        assert strategy == "Short"

    @pytest.mark.asyncio
    async def test_fallback_strategy_neutral_defaults_long(self, signal_generator):
        """Test neutral momentum defaults to Long."""
        signal_generator._price_cache = [100.0, 100.5, 99.5, 100.0, 100.0]

        strategy = await signal_generator._fallback_strategy(current_price=100.0)

        assert strategy == "Long"

    @pytest.mark.asyncio
    async def test_fallback_strategy_insufficient_data(self, signal_generator):
        """Test insufficient data defaults to Long."""
        signal_generator._price_cache = [100.0, 101.0]

        strategy = await signal_generator._fallback_strategy(current_price=102.0)

        assert strategy == "Long"

    @pytest.mark.asyncio
    async def test_fallback_strategy_exception(self, signal_generator):
        """Test exception handling defaults to Long."""
        signal_generator._price_cache = None  # Force an error

        strategy = await signal_generator._fallback_strategy(current_price=100.0)

        assert strategy == "Long"


class TestUpdatePriceHistory:
    """Test historical price data updates."""

    @pytest.mark.asyncio
    async def test_update_price_history_success(self, signal_generator, mock_ib_client):
        """Test successful price history update."""
        # Mock historical bars
        mock_bars = [Mock(close=100.0 + i) for i in range(60)]
        mock_ib_client.reqHistoricalData.return_value = mock_bars

        await signal_generator._update_price_history()

        assert len(signal_generator._price_cache) == 60
        assert signal_generator._price_cache[0] == 100.0
        assert signal_generator._price_cache[-1] == 159.0
        assert signal_generator._cache_updated is not None

    @pytest.mark.asyncio
    async def test_update_price_history_cached(self, signal_generator):
        """Test that cache is not updated if fresh."""
        signal_generator._cache_updated = datetime.utcnow()
        signal_generator._price_cache = [100.0] * 50

        await signal_generator._update_price_history()

        # Cache should remain unchanged
        assert len(signal_generator._price_cache) == 50

    @pytest.mark.asyncio
    async def test_update_price_history_expired_cache(self, signal_generator, mock_ib_client):
        """Test that expired cache is updated."""
        signal_generator._cache_updated = datetime.utcnow() - timedelta(hours=2)
        signal_generator._price_cache = [100.0] * 50

        mock_bars = [Mock(close=200.0 + i) for i in range(60)]
        mock_ib_client.reqHistoricalData.return_value = mock_bars

        await signal_generator._update_price_history()

        # Cache should be updated with new data
        assert signal_generator._price_cache[0] == 200.0
        assert len(signal_generator._price_cache) == 60

    @pytest.mark.asyncio
    async def test_update_price_history_no_data(self, signal_generator, mock_ib_client):
        """Test handling of empty historical data."""
        mock_ib_client.reqHistoricalData.return_value = []

        await signal_generator._update_price_history()

        # Cache should remain empty
        assert signal_generator._price_cache == []

    @pytest.mark.asyncio
    async def test_update_price_history_exception(self, signal_generator, mock_ib_client):
        """Test exception handling during update."""
        mock_ib_client.reqHistoricalData.side_effect = Exception("API error")

        await signal_generator._update_price_history()

        # Cache should remain unchanged
        assert signal_generator._price_cache == []


class TestGetNextExpiration:
    """Test expiration date calculation."""

    def test_get_next_expiration_monday(self, signal_generator):
        """Test expiration calculation from Monday."""
        monday = datetime(2025, 1, 6, 10, 0)  # Monday 10 AM

        expiration = signal_generator._get_next_expiration(monday)

        assert expiration == "20250110"  # Next Friday

    def test_get_next_expiration_friday_before_close(self, signal_generator):
        """Test expiration on Friday before market close."""
        friday = datetime(2025, 1, 10, 14, 0)  # Friday 2 PM

        expiration = signal_generator._get_next_expiration(friday)

        assert expiration == "20250110"  # Same Friday

    def test_get_next_expiration_friday_after_close(self, signal_generator):
        """Test expiration on Friday after market close."""
        friday = datetime(2025, 1, 10, 17, 0)  # Friday 5 PM

        expiration = signal_generator._get_next_expiration(friday)

        assert expiration == "20250117"  # Next Friday

    def test_get_next_expiration_saturday(self, signal_generator):
        """Test expiration calculation from Saturday."""
        saturday = datetime(2025, 1, 11, 10, 0)  # Saturday

        expiration = signal_generator._get_next_expiration(saturday)

        assert expiration == "20250117"  # Next Friday


class TestSelectStrikesByDelta:
    """Test strike selection based on delta."""

    @pytest.mark.asyncio
    async def test_select_strikes_long_strategy(self, signal_generator, mock_ib_client):
        """Test strike selection for Long (Bull Put) strategy."""
        # Mock option chain
        mock_chain = Mock()
        mock_chain.expirations = ["20250110"]
        mock_chain.strikes = [440.0, 442.0, 444.0, 446.0, 448.0, 450.0]
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        # Mock option Greeks
        mock_ticker_30 = Mock()
        mock_ticker_30.modelGreeks = Mock(delta=0.30)
        mock_ticker_15 = Mock()
        mock_ticker_15.modelGreeks = Mock(delta=0.15)

        mock_ib_client.reqMktData.side_effect = [mock_ticker_30, mock_ticker_15]

        strikes = await signal_generator._select_strikes_by_delta(
            current_price=450.0, expiration="20250110", strategy="Long"
        )

        assert strikes is not None
        strike_long, strike_short = strikes
        assert strike_long < strike_short  # Bull Put: long < short
        assert strike_long < 450.0  # Both below current price
        assert strike_short < 450.0

    @pytest.mark.asyncio
    async def test_select_strikes_short_strategy(self, signal_generator, mock_ib_client):
        """Test strike selection for Short (Bear Call) strategy."""
        # Mock option chain
        mock_chain = Mock()
        mock_chain.expirations = ["20250110"]
        mock_chain.strikes = [450.0, 452.0, 454.0, 456.0, 458.0, 460.0]
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        # Mock option Greeks
        mock_ticker_30 = Mock()
        mock_ticker_30.modelGreeks = Mock(delta=-0.30)
        mock_ticker_15 = Mock()
        mock_ticker_15.modelGreeks = Mock(delta=-0.15)

        mock_ib_client.reqMktData.side_effect = [mock_ticker_30, mock_ticker_15]

        strikes = await signal_generator._select_strikes_by_delta(
            current_price=450.0, expiration="20250110", strategy="Short"
        )

        assert strikes is not None
        strike_long, strike_short = strikes
        assert strike_long > strike_short  # Bear Call: long > short
        assert strike_long > 450.0  # Both above current price
        assert strike_short > 450.0

    @pytest.mark.asyncio
    async def test_select_strikes_no_chains(self, signal_generator, mock_ib_client):
        """Test handling when no option chains available."""
        mock_ib_client.reqSecDefOptParams.return_value = []

        strikes = await signal_generator._select_strikes_by_delta(
            current_price=450.0, expiration="20250110", strategy="Long"
        )

        assert strikes is None

    @pytest.mark.asyncio
    async def test_select_strikes_no_matching_expiration(self, signal_generator, mock_ib_client):
        """Test handling when expiration not found in chains."""
        mock_chain = Mock()
        mock_chain.expirations = ["20250117", "20250124"]
        mock_chain.strikes = [440.0, 442.0, 444.0]
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        strikes = await signal_generator._select_strikes_by_delta(
            current_price=450.0, expiration="20250110", strategy="Long"
        )

        assert strikes is None

    @pytest.mark.asyncio
    async def test_select_strikes_insufficient_strikes(self, signal_generator, mock_ib_client):
        """Test handling when insufficient strikes available."""
        mock_chain = Mock()
        mock_chain.expirations = ["20250110"]
        mock_chain.strikes = [448.0]  # Only one strike
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        strikes = await signal_generator._select_strikes_by_delta(
            current_price=450.0, expiration="20250110", strategy="Long"
        )

        assert strikes is None

    @pytest.mark.asyncio
    async def test_select_strikes_no_greeks_uses_fallback(self, signal_generator, mock_ib_client):
        """Test fallback when Greeks unavailable."""
        mock_chain = Mock()
        mock_chain.expirations = ["20250110"]
        mock_chain.strikes = [440.0, 442.0, 444.0, 446.0, 448.0, 450.0]
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        # Mock ticker with no Greeks
        mock_ticker = Mock()
        mock_ticker.modelGreeks = None
        mock_ib_client.reqMktData.return_value = mock_ticker

        with patch.object(
            signal_generator,
            "_fallback_strike_selection",
            return_value=(440.0, 444.0),
        ) as mock_fallback:
            strikes = await signal_generator._select_strikes_by_delta(
                current_price=450.0, expiration="20250110", strategy="Long"
            )

            assert strikes == (440.0, 444.0)
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_strikes_cancels_market_data(self, signal_generator, mock_ib_client):
        """Test that market data subscriptions are always cancelled."""
        mock_chain = Mock()
        mock_chain.expirations = ["20250110"]
        mock_chain.strikes = [440.0, 442.0]
        mock_ib_client.reqSecDefOptParams.return_value = [mock_chain]

        # Mock ticker that raises exception
        mock_ib_client.reqMktData.side_effect = Exception("Connection error")

        with patch.object(
            signal_generator,
            "_fallback_strike_selection",
            return_value=(440.0, 442.0),
        ):
            await signal_generator._select_strikes_by_delta(
                current_price=450.0, expiration="20250110", strategy="Long"
            )

            # cancelMktData should still be called despite exception
            assert mock_ib_client.cancelMktData.called


class TestFallbackStrikeSelection:
    """Test fallback strike selection using percentage offsets."""

    def test_fallback_long_strategy(self, signal_generator):
        """Test fallback for Long strategy."""
        strikes = [435.0, 440.0, 445.0, 450.0, 455.0, 460.0]

        result = signal_generator._fallback_strike_selection(
            current_price=450.0, strikes=strikes, strategy="Long"
        )

        assert result is not None
        strike_long, strike_short = result
        assert strike_long < strike_short
        assert strike_long < 450.0  # Below current price
        assert strike_short < 450.0

    def test_fallback_short_strategy(self, signal_generator):
        """Test fallback for Short strategy."""
        strikes = [440.0, 445.0, 450.0, 455.0, 460.0, 465.0]

        result = signal_generator._fallback_strike_selection(
            current_price=450.0, strikes=strikes, strategy="Short"
        )

        assert result is not None
        strike_long, strike_short = result
        assert strike_long > strike_short
        assert strike_long > 450.0  # Above current price
        assert strike_short > 450.0

    def test_fallback_exception(self, signal_generator):
        """Test exception handling in fallback."""
        result = signal_generator._fallback_strike_selection(
            current_price=450.0, strikes=[], strategy="Long"
        )

        assert result is None


class TestGenerateSignal:
    """Test complete signal generation."""

    @pytest.mark.asyncio
    async def test_generate_signal_success(self, signal_generator):
        """Test successful signal generation."""
        with (
            patch.object(signal_generator, "_get_current_price", return_value=450.0),
            patch.object(signal_generator, "_determine_strategy", return_value="Long"),
            patch.object(signal_generator, "_select_strikes_by_delta", return_value=(440.0, 445.0)),
        ):
            signal = await signal_generator.generate_signal()

            assert signal is not None
            assert signal["ticker"] == "QQQ"
            assert signal["strategy"] == "Long"
            assert signal["strike_long"] == 440.0
            assert signal["strike_short"] == 445.0
            assert signal["qty_per_leg"] == 1
            assert "date" in signal

    @pytest.mark.asyncio
    async def test_generate_signal_no_price(self, signal_generator):
        """Test signal generation failure when price unavailable."""
        with patch.object(signal_generator, "_get_current_price", return_value=None):
            signal = await signal_generator.generate_signal()

            assert signal is None

    @pytest.mark.asyncio
    async def test_generate_signal_no_strategy(self, signal_generator):
        """Test signal generation failure when strategy unclear."""
        with (
            patch.object(signal_generator, "_get_current_price", return_value=450.0),
            patch.object(signal_generator, "_determine_strategy", return_value=None),
        ):
            signal = await signal_generator.generate_signal()

            assert signal is None

    @pytest.mark.asyncio
    async def test_generate_signal_no_strikes(self, signal_generator):
        """Test signal generation failure when strikes unavailable."""
        with (
            patch.object(signal_generator, "_get_current_price", return_value=450.0),
            patch.object(signal_generator, "_determine_strategy", return_value="Long"),
            patch.object(signal_generator, "_select_strikes_by_delta", return_value=None),
        ):
            signal = await signal_generator.generate_signal()

            assert signal is None

    @pytest.mark.asyncio
    async def test_generate_signal_exception(self, signal_generator):
        """Test exception handling in signal generation."""
        with patch.object(signal_generator, "_get_current_price", side_effect=Exception("Error")):
            signal = await signal_generator.generate_signal()

            assert signal is None
