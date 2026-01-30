"""Add payment tables and update user_subscriptions for Razorpay

Revision ID: 006
Revises: 1d197469eec1
Create Date: 2026-01-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '1d197469eec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to user_subscriptions for Razorpay integration
    op.add_column('user_subscriptions',
        sa.Column('razorpay_subscription_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions',
        sa.Column('razorpay_customer_id', sa.String(255), nullable=True))
    op.add_column('user_subscriptions',
        sa.Column('billing_cycle', sa.String(20), server_default='monthly', nullable=True))
    op.add_column('user_subscriptions',
        sa.Column('auto_renew', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('user_subscriptions',
        sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('user_subscriptions',
        sa.Column('next_billing_date', sa.DateTime(), nullable=True))

    # Create indexes for Razorpay IDs
    op.create_index('idx_user_subscriptions_razorpay_sub',
        'user_subscriptions', ['razorpay_subscription_id'])
    op.create_index('idx_user_subscriptions_razorpay_cust',
        'user_subscriptions', ['razorpay_customer_id'])

    # Create payment_transactions table for audit trail
    op.create_table(
        'payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_subscription_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('user_subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('subscription_plans.id', ondelete='SET NULL'), nullable=True),

        # Razorpay identifiers
        sa.Column('razorpay_order_id', sa.String(255), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(255), nullable=True),
        sa.Column('razorpay_signature', sa.String(512), nullable=True),

        # Transaction details
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), server_default="'INR'", nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # pending, completed, failed, refunded
        sa.Column('payment_method', sa.String(50), nullable=True),  # card, upi, netbanking, wallet

        # Billing info
        sa.Column('billing_cycle', sa.String(20), nullable=True),  # monthly, yearly
        sa.Column('billing_start', sa.DateTime(), nullable=True),
        sa.Column('billing_end', sa.DateTime(), nullable=True),

        # Metadata
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('payment_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Idempotency
        sa.Column('idempotency_key', sa.String(255), nullable=True, unique=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Create indexes for payment_transactions
    op.create_index('idx_payment_transactions_user', 'payment_transactions', ['user_id'])
    op.create_index('idx_payment_transactions_status', 'payment_transactions', ['status'])
    op.create_index('idx_payment_transactions_razorpay_order',
        'payment_transactions', ['razorpay_order_id'])
    op.create_index('idx_payment_transactions_razorpay_payment',
        'payment_transactions', ['razorpay_payment_id'])
    op.create_index('idx_payment_transactions_created', 'payment_transactions', ['created_at'])

    # Seed subscription plans if they don't exist
    op.execute("""
        INSERT INTO subscription_plans (id, name, description, plan_type, price_monthly, price_yearly,
            performance_fee_percent, max_strategies, max_capital, features, is_active)
        SELECT
            gen_random_uuid(), 'Starter', 'Free tier for beginners', 'free', NULL, NULL,
            NULL, 1, 50000,
            '{"paper_trading": true, "basic_support": true}'::jsonb, true
        WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE name = 'Starter')
    """)

    op.execute("""
        INSERT INTO subscription_plans (id, name, description, plan_type, price_monthly, price_yearly,
            performance_fee_percent, max_strategies, max_capital, features, is_active)
        SELECT
            gen_random_uuid(), 'Trader', 'For active traders', 'subscription', 499, 4999,
            NULL, 3, 500000,
            '{"live_trading": true, "email_alerts": true, "basic_support": true}'::jsonb, true
        WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE name = 'Trader')
    """)

    op.execute("""
        INSERT INTO subscription_plans (id, name, description, plan_type, price_monthly, price_yearly,
            performance_fee_percent, max_strategies, max_capital, features, is_active)
        SELECT
            gen_random_uuid(), 'Professional', 'For serious traders', 'subscription', 1499, 14999,
            NULL, 10, 2500000,
            '{"live_trading": true, "sms_alerts": true, "email_alerts": true, "priority_support": true}'::jsonb, true
        WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE name = 'Professional')
    """)

    op.execute("""
        INSERT INTO subscription_plans (id, name, description, plan_type, price_monthly, price_yearly,
            performance_fee_percent, max_strategies, max_capital, features, is_active)
        SELECT
            gen_random_uuid(), 'Elite', 'Premium tier with profit sharing', 'performance', 999, 9999,
            10, NULL, NULL,
            '{"live_trading": true, "sms_alerts": true, "email_alerts": true, "dedicated_support": true, "custom_strategies": true}'::jsonb, true
        WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE name = 'Elite')
    """)


def downgrade() -> None:
    # Drop payment_transactions table
    op.drop_index('idx_payment_transactions_created', 'payment_transactions')
    op.drop_index('idx_payment_transactions_razorpay_payment', 'payment_transactions')
    op.drop_index('idx_payment_transactions_razorpay_order', 'payment_transactions')
    op.drop_index('idx_payment_transactions_status', 'payment_transactions')
    op.drop_index('idx_payment_transactions_user', 'payment_transactions')
    op.drop_table('payment_transactions')

    # Drop indexes from user_subscriptions
    op.drop_index('idx_user_subscriptions_razorpay_cust', 'user_subscriptions')
    op.drop_index('idx_user_subscriptions_razorpay_sub', 'user_subscriptions')

    # Drop columns from user_subscriptions
    op.drop_column('user_subscriptions', 'next_billing_date')
    op.drop_column('user_subscriptions', 'cancelled_at')
    op.drop_column('user_subscriptions', 'auto_renew')
    op.drop_column('user_subscriptions', 'billing_cycle')
    op.drop_column('user_subscriptions', 'razorpay_customer_id')
    op.drop_column('user_subscriptions', 'razorpay_subscription_id')

    # Note: Not deleting seeded plans in downgrade to preserve data
