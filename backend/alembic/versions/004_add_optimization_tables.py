"""Add optimization tables for Monte Carlo parameter optimization

Revision ID: 004
Revises: 003
Create Date: 2024-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Optimizations table - stores optimization run configuration and metadata
    op.create_table(
        'optimizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_backtest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), server_default="'pending'", nullable=False),
        # Backtest configuration (copied from source backtest)
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False, server_default="'NSE'"),
        sa.Column('interval', sa.String(20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(15, 2), nullable=False),
        # Optimization settings
        sa.Column('num_samples', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('parameter_ranges', postgresql.JSONB(), nullable=False),  # {"param": {"min": x, "max": y, "step": z}}
        sa.Column('objective_metric', sa.String(50), nullable=False, server_default="'total_return_percent'"),
        # Progress tracking
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('completed_samples', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_optimizations_user', 'optimizations', ['user_id'])
    op.create_index('idx_optimizations_strategy', 'optimizations', ['strategy_id'])
    op.create_index('idx_optimizations_status', 'optimizations', ['status'])
    op.create_index('idx_optimizations_created', 'optimizations', ['created_at'])

    # Optimization Results table - stores individual sample results
    op.create_table(
        'optimization_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('optimization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('optimizations.id', ondelete='CASCADE'), nullable=False),
        # Parameter values used for this sample
        sa.Column('parameters', postgresql.JSONB(), nullable=False),  # {"fast_ma_period": 9, "slow_ma_period": 21}
        # Key metrics (denormalized for fast queries and sorting)
        sa.Column('total_return', sa.Numeric(15, 4), nullable=True),
        sa.Column('total_return_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(10, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), server_default='0'),
        # Full metrics JSON (for detailed view)
        sa.Column('full_metrics', postgresql.JSONB(), nullable=True),
        # Flag for best result
        sa.Column('is_best', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_opt_results_optimization', 'optimization_results', ['optimization_id'])
    op.create_index('idx_opt_results_return', 'optimization_results', ['total_return_percent'])
    op.create_index('idx_opt_results_best', 'optimization_results', ['optimization_id', 'is_best'])


def downgrade() -> None:
    op.drop_table('optimization_results')
    op.drop_table('optimizations')
