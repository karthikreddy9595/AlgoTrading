"""Add config_params and selected_symbols to strategy_subscriptions

Revision ID: 003
Revises: 002
Create Date: 2024-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add config_params column for storing strategy signal parameters
    op.add_column(
        'strategy_subscriptions',
        sa.Column('config_params', postgresql.JSONB(), nullable=True, server_default='{}')
    )

    # Add selected_symbols column for user-selected trading symbols
    op.add_column(
        'strategy_subscriptions',
        sa.Column('selected_symbols', postgresql.ARRAY(sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('strategy_subscriptions', 'selected_symbols')
    op.drop_column('strategy_subscriptions', 'config_params')
