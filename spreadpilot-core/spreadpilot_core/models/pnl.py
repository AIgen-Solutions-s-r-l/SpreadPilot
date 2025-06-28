"""P&L data models for PostgreSQL database."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from enum import Enum

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class TradeType(str, Enum):
    """Trade type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class QuoteType(str, Enum):
    """Quote type enumeration."""
    BID = "BID"
    ASK = "ASK"
    LAST = "LAST"


class Trade(Base):
    """Trade records from IBKR fills."""
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(String(50), nullable=False, index=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False)  # e.g., "QQQ"
    contract_type = Column(String(10), nullable=False)  # "CALL" or "PUT"
    strike = Column(Numeric(10, 2), nullable=False)
    expiration = Column(Date, nullable=False)
    
    # Execution details
    trade_type = Column(String(4), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 4), nullable=False)
    commission = Column(Numeric(10, 4), nullable=False, default=0)
    
    # Identifiers
    order_id = Column(String(50), nullable=True)
    execution_id = Column(String(50), nullable=True)
    
    # Timestamps
    trade_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_trades_follower_time', 'follower_id', 'trade_time'),
        Index('ix_trades_symbol_exp', 'symbol', 'expiration'),
    )


class Quote(Base):
    """Real-time market quotes for positions."""
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contract details
    symbol = Column(String(20), nullable=False)
    contract_type = Column(String(10), nullable=False)  # "CALL", "PUT", "STK"
    strike = Column(Numeric(10, 2), nullable=True)  # NULL for stocks
    expiration = Column(Date, nullable=True)  # NULL for stocks
    
    # Quote data
    bid = Column(Numeric(10, 4), nullable=True)
    ask = Column(Numeric(10, 4), nullable=True)
    last = Column(Numeric(10, 4), nullable=True)
    volume = Column(Integer, nullable=True)
    
    # Timestamp
    quote_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_quotes_contract_time', 'symbol', 'contract_type', 'strike', 'expiration', 'quote_time'),
        Index('ix_quotes_time', 'quote_time'),
    )


class PnLIntraday(Base):
    """Intraday P&L snapshots (updated every 30 seconds)."""
    __tablename__ = "pnl_intraday"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(String(50), nullable=False, index=True)
    
    # Time period
    snapshot_time = Column(DateTime, nullable=False)
    trading_date = Column(Date, nullable=False)
    
    # P&L metrics
    realized_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    unrealized_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    total_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    
    # Position metrics
    position_count = Column(Integer, nullable=False, default=0)
    total_market_value = Column(Numeric(12, 4), nullable=False, default=0)
    
    # Commission tracking
    total_commission = Column(Numeric(10, 4), nullable=False, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_pnl_intraday_follower_time', 'follower_id', 'snapshot_time'),
        Index('ix_pnl_intraday_date', 'trading_date'),
    )


class PnLDaily(Base):
    """Daily P&L summaries (rolled up at 16:30 ET)."""
    __tablename__ = "pnl_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(String(50), nullable=False, index=True)
    
    # Time period
    trading_date = Column(Date, nullable=False)
    
    # Opening metrics
    opening_balance = Column(Numeric(12, 4), nullable=False, default=0)
    opening_positions = Column(Integer, nullable=False, default=0)
    
    # Daily P&L metrics
    realized_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    unrealized_pnl_start = Column(Numeric(12, 4), nullable=False, default=0)
    unrealized_pnl_end = Column(Numeric(12, 4), nullable=False, default=0)
    total_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    
    # Trading activity
    trades_count = Column(Integer, nullable=False, default=0)
    total_volume = Column(Integer, nullable=False, default=0)
    total_commission = Column(Numeric(10, 4), nullable=False, default=0)
    
    # Closing metrics
    closing_balance = Column(Numeric(12, 4), nullable=False, default=0)
    closing_positions = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    max_drawdown = Column(Numeric(12, 4), nullable=True)
    max_profit = Column(Numeric(12, 4), nullable=True)
    
    # Flags
    is_finalized = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    rollup_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_pnl_daily_follower_date', 'follower_id', 'trading_date'),
        Index('ix_pnl_daily_date', 'trading_date'),
    )


class PnLMonthly(Base):
    """Monthly P&L summaries (rolled up at 00:10 ET on 1st of month)."""
    __tablename__ = "pnl_monthly"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(String(50), nullable=False, index=True)
    
    # Time period
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    # Monthly P&L metrics
    realized_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    unrealized_pnl_start = Column(Numeric(12, 4), nullable=False, default=0)
    unrealized_pnl_end = Column(Numeric(12, 4), nullable=False, default=0)
    total_pnl = Column(Numeric(12, 4), nullable=False, default=0)
    
    # Monthly activity
    trading_days = Column(Integer, nullable=False, default=0)
    total_trades = Column(Integer, nullable=False, default=0)
    total_volume = Column(Integer, nullable=False, default=0)
    total_commission = Column(Numeric(10, 4), nullable=False, default=0)
    
    # Performance metrics
    best_day_pnl = Column(Numeric(12, 4), nullable=True)
    worst_day_pnl = Column(Numeric(12, 4), nullable=True)
    max_drawdown = Column(Numeric(12, 4), nullable=True)
    max_profit = Column(Numeric(12, 4), nullable=True)
    avg_daily_pnl = Column(Numeric(12, 4), nullable=True)
    
    # Win/Loss stats
    winning_days = Column(Integer, nullable=False, default=0)
    losing_days = Column(Integer, nullable=False, default=0)
    breakeven_days = Column(Integer, nullable=False, default=0)
    
    # Flags
    is_finalized = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    rollup_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_pnl_monthly_follower_period', 'follower_id', 'year', 'month'),
        Index('ix_pnl_monthly_period', 'year', 'month'),
    )