import uuid as uuid_module
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.deps import get_current_admin_user
from app.models import User, BlogPost, BlogCategory
from app.schemas import (
    BlogCategoryCreate,
    BlogCategoryUpdate,
    BlogCategoryResponse,
    BlogPostCreate,
    BlogPostUpdate,
    BlogPostResponse,
    BlogPostListResponse,
    BlogPostBulkUpload,
    BlogPostBulkResult,
    ImageUploadResponse,
)

router = APIRouter(prefix="/blog", tags=["Admin - Blog"])

# Image upload configuration
UPLOAD_DIR = Path("uploads/blog")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ==================== CATEGORY ENDPOINTS ====================

@router.get("/categories", response_model=List[BlogCategoryResponse])
async def admin_list_categories(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all categories (admin view)."""
    query = select(BlogCategory).order_by(BlogCategory.display_order, BlogCategory.name)

    if not include_inactive:
        query = query.where(BlogCategory.is_active.is_(True))

    result = await db.execute(query)
    categories = result.scalars().all()

    response = []
    for category in categories:
        # Count posts (all, not just published)
        count_query = select(func.count(BlogPost.id)).where(
            BlogPost.category_id == category.id
        )
        count_result = await db.execute(count_query)
        post_count = count_result.scalar() or 0

        response.append(
            BlogCategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                color=category.color,
                is_active=category.is_active,
                display_order=category.display_order,
                post_count=post_count,
                created_at=category.created_at,
            )
        )

    return response


@router.post("/categories", response_model=BlogCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: BlogCategoryCreate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new blog category."""
    # Check slug uniqueness
    result = await db.execute(
        select(BlogCategory).where(BlogCategory.slug == data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists",
        )

    category = BlogCategory(
        name=data.name,
        slug=data.slug,
        description=data.description,
        color=data.color,
        display_order=data.display_order,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return BlogCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        is_active=category.is_active,
        display_order=category.display_order,
        post_count=0,
        created_at=category.created_at,
    )


@router.patch("/categories/{category_id}", response_model=BlogCategoryResponse)
async def update_category(
    category_id: uuid_module.UUID,
    data: BlogCategoryUpdate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a blog category."""
    result = await db.execute(
        select(BlogCategory).where(BlogCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check slug uniqueness if updating slug
    if data.slug and data.slug != category.slug:
        slug_check = await db.execute(
            select(BlogCategory).where(BlogCategory.slug == data.slug)
        )
        if slug_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists",
            )

    # Apply updates
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    # Count posts
    count_query = select(func.count(BlogPost.id)).where(
        BlogPost.category_id == category.id
    )
    count_result = await db.execute(count_query)
    post_count = count_result.scalar() or 0

    return BlogCategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        is_active=category.is_active,
        display_order=category.display_order,
        post_count=post_count,
        created_at=category.created_at,
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: uuid_module.UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a blog category. Posts in this category will have their category set to null."""
    result = await db.execute(
        select(BlogCategory).where(BlogCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    await db.delete(category)
    await db.commit()

    return {"message": "Category deleted successfully"}


# ==================== POST ENDPOINTS ====================

@router.get("/posts", response_model=List[BlogPostListResponse])
async def admin_list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    category_id: Optional[uuid_module.UUID] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title"),
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all blog posts (including drafts) for admin."""
    query = select(BlogPost).order_by(BlogPost.created_at.desc())

    if status_filter:
        query = query.where(BlogPost.status == status_filter)

    if category_id:
        query = query.where(BlogPost.category_id == category_id)

    if search:
        query = query.where(BlogPost.title.ilike(f"%{search}%"))

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    response = []
    for post in posts:
        # Load category
        category_data = None
        if post.category_id:
            cat_result = await db.execute(
                select(BlogCategory).where(BlogCategory.id == post.category_id)
            )
            category_obj = cat_result.scalar_one_or_none()
            if category_obj:
                category_data = BlogCategoryResponse(
                    id=category_obj.id,
                    name=category_obj.name,
                    slug=category_obj.slug,
                    description=category_obj.description,
                    color=category_obj.color,
                    is_active=category_obj.is_active,
                    display_order=category_obj.display_order,
                    created_at=category_obj.created_at,
                )

        response.append(
            BlogPostListResponse(
                id=post.id,
                title=post.title,
                slug=post.slug,
                excerpt=post.excerpt,
                featured_image=post.featured_image,
                category=category_data,
                tags=post.tags,
                author_name=post.author_name,
                reading_time_minutes=post.reading_time_minutes,
                status=post.status,
                published_at=post.published_at,
                view_count=post.view_count,
                created_at=post.created_at,
            )
        )

    return response


@router.get("/posts/count")
async def admin_get_posts_count(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_id: Optional[uuid_module.UUID] = Query(None),
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get total count of posts for admin pagination."""
    query = select(func.count(BlogPost.id))

    if status_filter:
        query = query.where(BlogPost.status == status_filter)

    if category_id:
        query = query.where(BlogPost.category_id == category_id)

    result = await db.execute(query)
    count = result.scalar()

    return {"count": count}


@router.post("/posts", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: BlogPostCreate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new blog post."""
    # Check slug uniqueness
    result = await db.execute(
        select(BlogPost).where(BlogPost.slug == data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post with this slug already exists",
        )

    # Verify category exists if provided
    if data.category_id:
        cat_result = await db.execute(
            select(BlogCategory).where(BlogCategory.id == data.category_id)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found",
            )

    # Calculate reading time if not provided (rough estimate: 200 words/minute)
    reading_time = data.reading_time_minutes
    if not reading_time or reading_time == 5:  # default value
        word_count = len(data.content.split())
        reading_time = max(1, round(word_count / 200))

    post = BlogPost(
        title=data.title,
        slug=data.slug,
        excerpt=data.excerpt,
        content=data.content,
        featured_image=data.featured_image,
        featured_image_alt=data.featured_image_alt,
        category_id=data.category_id,
        tags=data.tags,
        author_name=data.author_name,
        reading_time_minutes=reading_time,
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        meta_keywords=data.meta_keywords,
        canonical_url=data.canonical_url,
        status=data.status,
        created_by_id=admin.id,
    )

    # Set published_at if publishing immediately
    if data.status == "published":
        post.published_at = datetime.utcnow()

    db.add(post)
    await db.commit()
    await db.refresh(post)

    return await _get_post_response(post, db)


@router.get("/posts/{post_id}", response_model=BlogPostResponse)
async def admin_get_post(
    post_id: uuid_module.UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a blog post by ID (admin view - includes drafts)."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    return await _get_post_response(post, db)


@router.patch("/posts/{post_id}", response_model=BlogPostResponse)
async def update_post(
    post_id: uuid_module.UUID,
    data: BlogPostUpdate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a blog post."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    # Check slug uniqueness if updating slug
    if data.slug and data.slug != post.slug:
        slug_check = await db.execute(
            select(BlogPost).where(BlogPost.slug == data.slug)
        )
        if slug_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post with this slug already exists",
            )

    # Verify category exists if updating category
    if data.category_id:
        cat_result = await db.execute(
            select(BlogCategory).where(BlogCategory.id == data.category_id)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found",
            )

    # Apply updates
    update_dict = data.model_dump(exclude_unset=True)

    # Handle status change to published
    if data.status == "published" and post.status != "published":
        post.published_at = datetime.utcnow()

    for field, value in update_dict.items():
        setattr(post, field, value)

    post.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(post)

    return await _get_post_response(post, db)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: uuid_module.UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a blog post."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    await db.delete(post)
    await db.commit()

    return {"message": "Blog post deleted successfully"}


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: uuid_module.UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft blog post."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    if post.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post is already published",
        )

    post.status = "published"
    post.published_at = datetime.utcnow()
    post.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Blog post published successfully"}


@router.post("/posts/{post_id}/unpublish")
async def unpublish_post(
    post_id: uuid_module.UUID,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Unpublish a blog post (revert to draft)."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    if post.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post is not published",
        )

    post.status = "draft"
    post.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Blog post unpublished successfully"}


# ==================== BULK UPLOAD ====================

@router.post("/posts/bulk", response_model=BlogPostBulkResult)
async def bulk_upload_posts(
    data: BlogPostBulkUpload,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk create blog posts from JSON.

    Expected format:
    {
        "posts": [
            {
                "title": "Post Title",
                "slug": "post-slug",
                "content": "# Markdown content...",
                "category_slug": "category-slug",  // optional
                "tags": ["tag1", "tag2"],
                "status": "draft" or "published"
            }
        ]
    }
    """
    created = 0
    failed = 0
    errors = []

    # Build category slug to ID mapping
    cat_result = await db.execute(select(BlogCategory))
    categories = {cat.slug: cat.id for cat in cat_result.scalars().all()}

    for idx, post_data in enumerate(data.posts):
        try:
            # Check slug uniqueness
            slug_check = await db.execute(
                select(BlogPost).where(BlogPost.slug == post_data.slug)
            )
            if slug_check.scalar_one_or_none():
                errors.append({
                    "index": idx,
                    "slug": post_data.slug,
                    "error": "Slug already exists"
                })
                failed += 1
                continue

            # Resolve category ID from slug
            category_id = None
            if post_data.category_slug:
                category_id = categories.get(post_data.category_slug)
                if not category_id:
                    errors.append({
                        "index": idx,
                        "slug": post_data.slug,
                        "error": f"Category '{post_data.category_slug}' not found"
                    })
                    failed += 1
                    continue

            # Calculate reading time
            word_count = len(post_data.content.split())
            reading_time = post_data.reading_time_minutes or max(1, round(word_count / 200))

            post = BlogPost(
                title=post_data.title,
                slug=post_data.slug,
                excerpt=post_data.excerpt,
                content=post_data.content,
                featured_image=post_data.featured_image,
                featured_image_alt=post_data.featured_image_alt,
                category_id=category_id,
                tags=post_data.tags,
                author_name=post_data.author_name,
                reading_time_minutes=reading_time,
                meta_title=post_data.meta_title,
                meta_description=post_data.meta_description,
                meta_keywords=post_data.meta_keywords,
                status=post_data.status,
                created_by_id=admin.id,
            )

            if post_data.status == "published":
                post.published_at = datetime.utcnow()

            db.add(post)
            created += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "slug": post_data.slug if hasattr(post_data, 'slug') else "unknown",
                "error": str(e)
            })
            failed += 1

    await db.commit()

    return BlogPostBulkResult(
        total=len(data.posts),
        created=created,
        failed=failed,
        errors=errors,
    )


# ==================== IMAGE UPLOAD ====================

@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin_user),
):
    """
    Upload an image for blog posts.
    Returns the path to use in blog post content.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB.",
        )

    # Generate unique filename
    filename = f"{uuid_module.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    # Ensure directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Save file
    with open(filepath, "wb") as f:
        f.write(contents)

    return ImageUploadResponse(
        path=f"/uploads/blog/{filename}",
        filename=filename,
    )


# ==================== HELPER FUNCTIONS ====================

async def _get_post_response(post: BlogPost, db: AsyncSession) -> BlogPostResponse:
    """Build BlogPostResponse with category data."""
    category_data = None
    if post.category_id:
        cat_result = await db.execute(
            select(BlogCategory).where(BlogCategory.id == post.category_id)
        )
        category_obj = cat_result.scalar_one_or_none()
        if category_obj:
            category_data = BlogCategoryResponse(
                id=category_obj.id,
                name=category_obj.name,
                slug=category_obj.slug,
                description=category_obj.description,
                color=category_obj.color,
                is_active=category_obj.is_active,
                display_order=category_obj.display_order,
                created_at=category_obj.created_at,
            )

    return BlogPostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content,
        featured_image=post.featured_image,
        featured_image_alt=post.featured_image_alt,
        category_id=post.category_id,
        tags=post.tags,
        author_name=post.author_name,
        reading_time_minutes=post.reading_time_minutes,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        meta_keywords=post.meta_keywords,
        canonical_url=post.canonical_url,
        status=post.status,
        published_at=post.published_at,
        view_count=post.view_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        category=category_data,
    )
