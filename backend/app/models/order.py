from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("strategy_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Numeric(15, 4), nullable=False)
    current_price = Column(Numeric(15, 4), nullable=True)
    unrealized_pnl = Column(Numeric(15, 2), nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("StrategySubscription", back_populates="positions")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("strategy_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_order_id = Column(String(100), nullable=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, SL, SL-M
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(15, 4), nullable=True)
    trigger_price = Column(Numeric(15, 4), nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending, placed, filled, rejected, cancelled
    filled_quantity = Column(Integer, default=0)
    filled_price = Column(Numeric(15, 4), nullable=True)
    reason = Column(Text, nullable=True)  # Why strategy generated this order
    broker_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("StrategySubscription", back_populates="orders")
    entry_trades = relationship("Trade", foreign_keys="Trade.entry_order_id", back_populates="entry_order")
    exit_trades = relationship("Trade", foreign_keys="Trade.exit_order_id", back_populates="exit_order")


class OrderLog(Base):
    """
    Comprehensive log of all order events for debugging and testing.

    Captures every order attempt (success, failure, dry-run) with full context
    to help verify if orders are being sent to the broker correctly.
    """
    __tablename__ = "order_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("strategy_subscriptions.id", ondelete="CASCADE"), nullable=True, index=True)  # Null for test orders
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)  # Null for dry-run

    # Order details
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(15, 4), nullable=True)
    trigger_price = Column(Numeric(15, 4), nullable=True)

    # Execution details
    event_type = Column(String(30), nullable=False, index=True)  # generated, dry_run, submitted, placed, filled, rejected, failed
    is_dry_run = Column(Boolean, default=False, index=True)
    is_test_order = Column(Boolean, default=False)  # True for broker test orders
    success = Column(Boolean, nullable=True)

    # Broker interaction
    broker_order_id = Column(String(100), nullable=True)
    broker_name = Column(String(50), nullable=True)
    broker_request = Column(JSONB, nullable=True)  # Request payload sent to broker
    broker_response = Column(JSONB, nullable=True)  # Response from broker
    error_message = Column(Text, nullable=True)

    # Context
    strategy_name = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)  # Why the order was generated
    market_price = Column(Numeric(15, 4), nullable=True)  # Price at time of order

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    subscription = relationship("StrategySubscription")
