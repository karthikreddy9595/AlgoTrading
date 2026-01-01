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
