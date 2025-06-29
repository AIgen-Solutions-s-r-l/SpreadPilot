"""Initial P&L schema creation

Revision ID: 001
Revises:
Create Date: 2025-06-28 10:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create trades table
    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", sa.String(length=50), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("contract_type", sa.String(length=10), nullable=False),
        sa.Column("strike", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("expiration", sa.Date(), nullable=False),
        sa.Column("trade_type", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("commission", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=True),
        sa.Column("execution_id", sa.String(length=50), nullable=True),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_follower_id", "trades", ["follower_id"], unique=False)
    op.create_index(
        "ix_trades_follower_time", "trades", ["follower_id", "trade_time"], unique=False
    )
    op.create_index(
        "ix_trades_symbol_exp", "trades", ["symbol", "expiration"], unique=False
    )

    # Create quotes table
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("contract_type", sa.String(length=10), nullable=False),
        sa.Column("strike", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("expiration", sa.Date(), nullable=True),
        sa.Column("bid", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ask", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("last", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("quote_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_quotes_contract_time",
        "quotes",
        ["symbol", "contract_type", "strike", "expiration", "quote_time"],
        unique=False,
    )
    op.create_index("ix_quotes_time", "quotes", ["quote_time"], unique=False)

    # Create pnl_intraday table
    op.create_table(
        "pnl_intraday",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", sa.String(length=50), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("total_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("position_count", sa.Integer(), nullable=False),
        sa.Column(
            "total_market_value", sa.Numeric(precision=12, scale=4), nullable=False
        ),
        sa.Column(
            "total_commission", sa.Numeric(precision=10, scale=4), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pnl_intraday_follower_id", "pnl_intraday", ["follower_id"], unique=False
    )
    op.create_index(
        "ix_pnl_intraday_follower_time",
        "pnl_intraday",
        ["follower_id", "snapshot_time"],
        unique=False,
    )
    op.create_index(
        "ix_pnl_intraday_date", "pnl_intraday", ["trading_date"], unique=False
    )

    # Create pnl_daily table
    op.create_table(
        "pnl_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", sa.String(length=50), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("opening_positions", sa.Integer(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column(
            "unrealized_pnl_start", sa.Numeric(precision=12, scale=4), nullable=False
        ),
        sa.Column(
            "unrealized_pnl_end", sa.Numeric(precision=12, scale=4), nullable=False
        ),
        sa.Column("total_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("trades_count", sa.Integer(), nullable=False),
        sa.Column("total_volume", sa.Integer(), nullable=False),
        sa.Column(
            "total_commission", sa.Numeric(precision=10, scale=4), nullable=False
        ),
        sa.Column("closing_balance", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("closing_positions", sa.Integer(), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_profit", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("is_finalized", sa.Boolean(), nullable=False),
        sa.Column("rollup_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pnl_daily_follower_id", "pnl_daily", ["follower_id"], unique=False
    )
    op.create_index(
        "ix_pnl_daily_follower_date",
        "pnl_daily",
        ["follower_id", "trading_date"],
        unique=False,
    )
    op.create_index("ix_pnl_daily_date", "pnl_daily", ["trading_date"], unique=False)

    # Create pnl_monthly table
    op.create_table(
        "pnl_monthly",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column(
            "unrealized_pnl_start", sa.Numeric(precision=12, scale=4), nullable=False
        ),
        sa.Column(
            "unrealized_pnl_end", sa.Numeric(precision=12, scale=4), nullable=False
        ),
        sa.Column("total_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("trading_days", sa.Integer(), nullable=False),
        sa.Column("total_trades", sa.Integer(), nullable=False),
        sa.Column("total_volume", sa.Integer(), nullable=False),
        sa.Column(
            "total_commission", sa.Numeric(precision=10, scale=4), nullable=False
        ),
        sa.Column("best_day_pnl", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("worst_day_pnl", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("max_profit", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("avg_daily_pnl", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("winning_days", sa.Integer(), nullable=False),
        sa.Column("losing_days", sa.Integer(), nullable=False),
        sa.Column("breakeven_days", sa.Integer(), nullable=False),
        sa.Column("is_finalized", sa.Boolean(), nullable=False),
        sa.Column("rollup_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pnl_monthly_follower_id", "pnl_monthly", ["follower_id"], unique=False
    )
    op.create_index(
        "ix_pnl_monthly_follower_period",
        "pnl_monthly",
        ["follower_id", "year", "month"],
        unique=False,
    )
    op.create_index(
        "ix_pnl_monthly_period", "pnl_monthly", ["year", "month"], unique=False
    )


def downgrade() -> None:
    op.drop_table("pnl_monthly")
    op.drop_table("pnl_daily")
    op.drop_table("pnl_intraday")
    op.drop_table("quotes")
    op.drop_table("trades")
