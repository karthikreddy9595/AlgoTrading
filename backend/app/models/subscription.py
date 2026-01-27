from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, Integer, ARRAY, ForeignKey, Time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    plan_type = Column(String(20), nullable=False)  # free, subscription, performance
    price_monthly = Column(Numeric(10, 2), nullable=True)
    price_yearly = Column(Numeric(10, 2), nullable=True)
    performance_fee_percent = Column(Numeric(5, 2), nullable=True)  # For performance-based
    max_strategies = Column(Integer, nullable=True)
    max_capital = Column(Numeric(15, 2), nullable=True)
    features = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_subscriptions = relationship("UserSubscription", back_populates="plan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(String(20), default="active")  # active, cancelled, expired
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    payment_provider = Column(String(50), nullable=True)  # razorpay, stripe
    payment_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_subscription")
    plan = relationship("SubscriptionPlan", back_populates="user_subscriptions")


class StrategySubscription(Base):
    __tablename__ = "strategy_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_connection_id = Column(UUID(as_uuid=True), ForeignKey("broker_connections.id"), nullable=True)
    status = Column(String(20), default="inactive")  # inactive, active, paused, stopped
    capital_allocated = Column(Numeric(15, 2), nullable=False)
    is_paper_trading = Column(Boolean, default=True)
    dry_run = Column(Boolean, default=False)  # If True, orders are logged but not placed

    # Risk settings
    max_drawdown_percent = Column(Numeric(5, 2), default=10)
    daily_loss_limit = Column(Numeric(15, 2), nullable=True)
    per_trade_stop_loss_percent = Column(Numeric(5, 2), default=2)
    max_positions = Column(Integer, default=5)

    # Strategy configuration (signal parameters)
    config_params = Column(JSONB, nullable=True, default={})
    selected_symbols = Column(ARRAY(Text), nullable=True)

    # Scheduling
    scheduled_start = Column(Time, nullable=True)
    scheduled_stop = Column(Time, nullable=True)
    active_days = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5])  # Mon-Fri

    # State
    current_pnl = Column(Numeric(15, 2), default=0)
    today_pnl = Column(Numeric(15, 2), default=0)
    last_started_at = Column(DateTime, nullable=True)
    last_stopped_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="strategy_subscriptions")
    strategy = relationship("Strategy", back_populates="subscriptions")
    broker_connection = relationship("BrokerConnection", back_populates="strategy_subscriptions")
    positions = relationship("Position", back_populates="subscription", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="subscription", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        {"extend_existing": True},
    )
