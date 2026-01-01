from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    author = Column(String(255), default="Platform")
    min_capital = Column(Numeric(15, 2), default=10000)
    expected_return_percent = Column(Numeric(5, 2), nullable=True)
    max_drawdown_percent = Column(Numeric(5, 2), nullable=True)
    timeframe = Column(String(20), nullable=True)  # 1min, 5min, etc.
    supported_symbols = Column(ARRAY(Text), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    git_repo_url = Column(String(500), nullable=True)
    git_branch = Column(String(100), default="main")
    git_commit_hash = Column(String(40), nullable=True)
    module_path = Column(String(255), nullable=False)  # e.g., strategies.implementations.ma_crossover
    class_name = Column(String(255), nullable=False)   # e.g., SimpleMovingAverageCrossover
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete-orphan")
    subscriptions = relationship("StrategySubscription", back_populates="strategy")


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    git_commit_hash = Column(String(40), nullable=True)
    changelog = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="versions")
