from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Category Schemas
class BlogCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    color: str = Field(default="#6366f1", pattern="^#[0-9a-fA-F]{6}$")


class BlogCategoryCreate(BlogCategoryBase):
    display_order: int = 0


class BlogCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#[0-9a-fA-F]{6}$")
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class BlogCategoryResponse(BlogCategoryBase):
    id: UUID
    is_active: bool
    display_order: int
    post_count: Optional[int] = None  # Computed field
    created_at: datetime

    class Config:
        from_attributes = True


# Post Schemas
class BlogPostBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    slug: str = Field(..., min_length=5, max_length=255, pattern="^[a-z0-9-]+$")
    excerpt: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=50)
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = Field(None, max_length=255)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    author_name: str = Field(default="ArthaQuant Team", max_length=255)
    reading_time_minutes: int = Field(default=5, ge=1, le=120)
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    meta_keywords: Optional[List[str]] = None
    canonical_url: Optional[str] = Field(None, max_length=500)


class BlogPostCreate(BlogPostBase):
    status: str = Field(default="draft", pattern="^(draft|published)$")


class BlogPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    slug: Optional[str] = Field(None, min_length=5, max_length=255, pattern="^[a-z0-9-]+$")
    excerpt: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=50)
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = Field(None, max_length=255)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    author_name: Optional[str] = Field(None, max_length=255)
    reading_time_minutes: Optional[int] = Field(None, ge=1, le=120)
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    meta_keywords: Optional[List[str]] = None
    canonical_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")


class BlogPostResponse(BlogPostBase):
    id: UUID
    status: str
    published_at: Optional[datetime]
    view_count: int
    created_at: datetime
    updated_at: datetime
    category: Optional[BlogCategoryResponse] = None

    class Config:
        from_attributes = True


class BlogPostListResponse(BaseModel):
    """Lightweight response for list views"""
    id: UUID
    title: str
    slug: str
    excerpt: Optional[str]
    featured_image: Optional[str]
    category: Optional[BlogCategoryResponse]
    tags: Optional[List[str]]
    author_name: str
    reading_time_minutes: int
    status: str
    published_at: Optional[datetime]
    view_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# Bulk Upload Schemas
class BlogPostBulkItem(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    slug: str = Field(..., min_length=5, max_length=255, pattern="^[a-z0-9-]+$")
    excerpt: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=50)
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    category_slug: Optional[str] = None  # Use slug instead of ID for easier bulk upload
    tags: Optional[List[str]] = None
    author_name: str = Field(default="ArthaQuant Team", max_length=255)
    reading_time_minutes: int = Field(default=5, ge=1, le=120)
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    meta_keywords: Optional[List[str]] = None
    status: str = Field(default="draft", pattern="^(draft|published)$")


class BlogPostBulkUpload(BaseModel):
    posts: List[BlogPostBulkItem]


class BlogPostBulkResult(BaseModel):
    total: int
    created: int
    failed: int
    errors: List[dict]


# Image Upload Response
class ImageUploadResponse(BaseModel):
    path: str
    filename: str
