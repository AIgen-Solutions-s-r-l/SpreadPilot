"""Add commission_monthly table

Revision ID: 002
Revises: 001
Create Date: 2025-06-28 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create commission_monthly table
    op.create_table(
        "commission_monthly",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("follower_id", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("monthly_pnl", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("commission_pct", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("commission_amount", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("commission_currency", sa.String(length=3), nullable=False),
        sa.Column("follower_iban", sa.String(length=34), nullable=False),
        sa.Column("follower_email", sa.String(length=255), nullable=False),
        sa.Column("is_payable", sa.Boolean(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_commission_monthly_follower_id",
        "commission_monthly",
        ["follower_id"],
        unique=False,
    )
    op.create_index(
        "ix_commission_monthly_follower_period",
        "commission_monthly",
        ["follower_id", "year", "month"],
        unique=False,
    )
    op.create_index(
        "ix_commission_monthly_period",
        "commission_monthly",
        ["year", "month"],
        unique=False,
    )
    op.create_index(
        "ix_commission_monthly_payable",
        "commission_monthly",
        ["is_payable"],
        unique=False,
    )
    op.create_index("ix_commission_monthly_paid", "commission_monthly", ["is_paid"], unique=False)


def downgrade() -> None:
    op.drop_table("commission_monthly")
