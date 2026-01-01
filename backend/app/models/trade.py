from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("strategy_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    exit_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(15, 4), nullable=False)
    exit_price = Column(Numeric(15, 4), nullable=True)
    pnl = Column(Numeric(15, 2), nullable=True)
    pnl_percent = Column(Numeric(8, 4), nullable=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), default="open")  # open, closed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    subscription = relationship("StrategySubscription", back_populates="trades")
    entry_order = relationship("Order", foreign_keys=[entry_order_id], back_populates="entry_trades")
    exit_order = relationship("Order", foreign_keys=[exit_order_id], back_populates="exit_trades")
