"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_admin', sa.Boolean(), server_default='false'),
        sa.Column('email_verified', sa.Boolean(), server_default='false'),
        sa.Column('phone_verified', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # OAuth Accounts table
    op.create_table(
        'oauth_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
    )

    # Broker Connections table
    op.create_table(
        'broker_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('broker', sa.String(50), nullable=False),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column('api_secret', sa.Text(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('client_id', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'broker', name='uq_user_broker'),
    )

    # Strategies table
    op.create_table(
        'strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('long_description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('author', sa.String(255), server_default="'Platform'"),
        sa.Column('min_capital', sa.Numeric(15, 2), server_default='10000'),
        sa.Column('expected_return_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_drawdown_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('timeframe', sa.String(20), nullable=True),
        sa.Column('supported_symbols', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_featured', sa.Boolean(), server_default='false'),
        sa.Column('git_repo_url', sa.String(500), nullable=True),
        sa.Column('git_branch', sa.String(100), server_default="'main'"),
        sa.Column('git_commit_hash', sa.String(40), nullable=True),
        sa.Column('module_path', sa.String(255), nullable=False),
        sa.Column('class_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Strategy Versions table
    op.create_table(
        'strategy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('git_commit_hash', sa.String(40), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Subscription Plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('plan_type', sa.String(20), nullable=False),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=True),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=True),
        sa.Column('performance_fee_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_strategies', sa.Integer(), nullable=True),
        sa.Column('max_capital', sa.Numeric(15, 2), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # User Subscriptions table
    op.create_table(
        'user_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default="'active'"),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('payment_provider', sa.String(50), nullable=True),
        sa.Column('payment_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Strategy Subscriptions table
    op.create_table(
        'strategy_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('broker_connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('broker_connections.id'), nullable=True),
        sa.Column('status', sa.String(20), server_default="'inactive'"),
        sa.Column('capital_allocated', sa.Numeric(15, 2), nullable=False),
        sa.Column('is_paper_trading', sa.Boolean(), server_default='true'),
        sa.Column('max_drawdown_percent', sa.Numeric(5, 2), server_default='10'),
        sa.Column('daily_loss_limit', sa.Numeric(15, 2), nullable=True),
        sa.Column('per_trade_stop_loss_percent', sa.Numeric(5, 2), server_default='2'),
        sa.Column('max_positions', sa.Integer(), server_default='5'),
        sa.Column('scheduled_start', sa.Time(), nullable=True),
        sa.Column('scheduled_stop', sa.Time(), nullable=True),
        sa.Column('active_days', postgresql.ARRAY(sa.Integer()), server_default='{1,2,3,4,5}'),
        sa.Column('current_pnl', sa.Numeric(15, 2), server_default='0'),
        sa.Column('today_pnl', sa.Numeric(15, 2), server_default='0'),
        sa.Column('last_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_stopped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'strategy_id', name='uq_user_strategy'),
    )

    # Positions table
    op.create_table(
        'positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategy_subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('avg_price', sa.Numeric(15, 4), nullable=False),
        sa.Column('current_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(15, 2), nullable=True),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_positions_subscription', 'positions', ['subscription_id'])

    # Orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategy_subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('broker_order_id', sa.String(100), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('transaction_type', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(15, 4), nullable=True),
        sa.Column('trigger_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('status', sa.String(20), server_default="'pending'"),
        sa.Column('filled_quantity', sa.Integer(), server_default='0'),
        sa.Column('filled_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('broker_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_orders_subscription', 'orders', ['subscription_id'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_created', 'orders', ['created_at'])

    # Trades table
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('strategy_subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entry_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('exit_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_price', sa.Numeric(15, 4), nullable=False),
        sa.Column('exit_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('pnl', sa.Numeric(15, 2), nullable=True),
        sa.Column('pnl_percent', sa.Numeric(8, 4), nullable=True),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), server_default="'open'"),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_trades_subscription', 'trades', ['subscription_id'])
    op.create_index('idx_trades_created', 'trades', ['created_at'])

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_notifications_user', 'notifications', ['user_id', 'is_read'])

    # Notification Preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('email_enabled', sa.Boolean(), server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), server_default='false'),
        sa.Column('in_app_enabled', sa.Boolean(), server_default='true'),
        sa.Column('trade_alerts', sa.Boolean(), server_default='true'),
        sa.Column('daily_summary', sa.Boolean(), server_default='true'),
        sa.Column('risk_alerts', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('audit_logs')
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.drop_table('trades')
    op.drop_table('orders')
    op.drop_table('positions')
    op.drop_table('strategy_subscriptions')
    op.drop_table('user_subscriptions')
    op.drop_table('subscription_plans')
    op.drop_table('strategy_versions')
    op.drop_table('strategies')
    op.drop_table('broker_connections')
    op.drop_table('oauth_accounts')
    op.drop_table('users')
