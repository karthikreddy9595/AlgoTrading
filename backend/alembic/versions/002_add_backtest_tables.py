"""Add backtest tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backtests table - stores backtest configuration and metadata
    op.create_table(
        'backtests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), server_default="'pending'", nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False, server_default="'NSE'"),
        sa.Column('interval', sa.String(20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(15, 2), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_backtests_user', 'backtests', ['user_id'])
    op.create_index('idx_backtests_strategy', 'backtests', ['strategy_id'])
    op.create_index('idx_backtests_status', 'backtests', ['status'])
    op.create_index('idx_backtests_created', 'backtests', ['created_at'])

    # Backtest Results table - stores computed metrics
    op.create_table(
        'backtest_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('backtest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtests.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('total_return', sa.Numeric(15, 4), nullable=True),
        sa.Column('total_return_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('cagr', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('avg_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), server_default='0'),
        sa.Column('winning_trades', sa.Integer(), server_default='0'),
        sa.Column('losing_trades', sa.Integer(), server_default='0'),
        sa.Column('avg_trade_duration', sa.Integer(), nullable=True),  # in seconds
        sa.Column('calmar_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('final_capital', sa.Numeric(15, 2), nullable=True),
        sa.Column('max_capital', sa.Numeric(15, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Backtest Trades table - stores individual trades
    op.create_table(
        'backtest_trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('backtest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('signal', sa.String(20), nullable=False),  # BUY, SELL, EXIT_LONG, EXIT_SHORT
        sa.Column('entry_price', sa.Numeric(15, 4), nullable=False),
        sa.Column('exit_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('pnl', sa.Numeric(15, 4), nullable=True),
        sa.Column('pnl_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_open', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_backtest_trades_backtest', 'backtest_trades', ['backtest_id'])
    op.create_index('idx_backtest_trades_entry_time', 'backtest_trades', ['entry_time'])

    # Backtest Equity Curve table - stores equity values over time for charting
    op.create_table(
        'backtest_equity_curve',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('backtest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('backtests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('equity', sa.Numeric(15, 4), nullable=False),
        sa.Column('drawdown', sa.Numeric(10, 4), nullable=True),
    )
    op.create_index('idx_backtest_equity_backtest', 'backtest_equity_curve', ['backtest_id'])
    op.create_index('idx_backtest_equity_timestamp', 'backtest_equity_curve', ['timestamp'])


def downgrade() -> None:
    op.drop_table('backtest_equity_curve')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_results')
    op.drop_table('backtests')
