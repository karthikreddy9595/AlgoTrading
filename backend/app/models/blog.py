from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")  # Hex color for UI badges
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("BlogPost", back_populates="category")


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core content
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    excerpt = Column(String(500), nullable=True)  # Short summary for cards
    content = Column(Text, nullable=False)  # Markdown content

    # Media
    featured_image = Column(String(500), nullable=True)  # Path to image
    featured_image_alt = Column(String(255), nullable=True)

    # Organization
    category_id = Column(UUID(as_uuid=True), ForeignKey("blog_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    tags = Column(ARRAY(Text), nullable=True)

    # Metadata
    author_name = Column(String(255), default="ArthaQuant Team")
    reading_time_minutes = Column(Integer, default=5)

    # SEO fields
    meta_title = Column(String(70), nullable=True)  # Falls back to title
    meta_description = Column(String(160), nullable=True)  # Falls back to excerpt
    meta_keywords = Column(ARRAY(Text), nullable=True)
    canonical_url = Column(String(500), nullable=True)

    # Publishing workflow
    status = Column(String(20), default="draft", index=True)  # draft, published, archived
    published_at = Column(DateTime, nullable=True, index=True)

    # Analytics
    view_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Created by (admin user)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    category = relationship("BlogCategory", back_populates="posts")
    created_by = relationship("User")
