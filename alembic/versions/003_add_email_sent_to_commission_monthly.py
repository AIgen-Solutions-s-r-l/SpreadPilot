"""Add email sent field to commission_monthly table

Revision ID: 003
Revises: 002
Create Date: 2025-06-28 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sent column to commission_monthly table
    op.add_column('commission_monthly', 
        sa.Column('sent', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add sent_at timestamp
    op.add_column('commission_monthly',
        sa.Column('sent_at', sa.DateTime(), nullable=True)
    )
    
    # Create index for sent status
    op.create_index('ix_commission_monthly_sent', 'commission_monthly', ['sent'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_commission_monthly_sent', table_name='commission_monthly')
    op.drop_column('commission_monthly', 'sent_at')
    op.drop_column('commission_monthly', 'sent')