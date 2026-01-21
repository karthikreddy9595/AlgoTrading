from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.models import BlogPost, BlogCategory
from app.schemas import (
    BlogCategoryResponse,
    BlogPostResponse,
    BlogPostListResponse,
)

router = APIRouter(prefix="/blog", tags=["Blog"])


@router.get("/posts", response_model=List[BlogPostListResponse])
async def list_published_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in title and excerpt"),
    db: AsyncSession = Depends(get_db),
):
    """
    List published blog posts with pagination and filtering.
    Public endpoint - no authentication required.
    """
    query = (
        select(BlogPost)
        .where(BlogPost.status == "published")
        .order_by(BlogPost.published_at.desc())
    )

    # Filter by category slug
    if category:
        query = query.join(BlogCategory).where(BlogCategory.slug == category)

    # Filter by tag
    if tag:
        query = query.where(BlogPost.tags.contains([tag]))

    # Search in title and excerpt
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (BlogPost.title.ilike(search_term)) |
            (BlogPost.excerpt.ilike(search_term))
        )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    # Load category relationship for each post
    response = []
    for post in posts:
        post_dict = {
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "excerpt": post.excerpt,
            "featured_image": post.featured_image,
            "tags": post.tags,
            "author_name": post.author_name,
            "reading_time_minutes": post.reading_time_minutes,
            "status": post.status,
            "published_at": post.published_at,
            "view_count": post.view_count,
            "created_at": post.created_at,
            "category": None,
        }
        if post.category_id:
            cat_result = await db.execute(
                select(BlogCategory).where(BlogCategory.id == post.category_id)
            )
            category_obj = cat_result.scalar_one_or_none()
            if category_obj:
                post_dict["category"] = {
                    "id": category_obj.id,
                    "name": category_obj.name,
                    "slug": category_obj.slug,
                    "description": category_obj.description,
                    "color": category_obj.color,
                    "is_active": category_obj.is_active,
                    "display_order": category_obj.display_order,
                    "created_at": category_obj.created_at,
                }
        response.append(post_dict)

    return response


@router.get("/posts/count")
async def get_posts_count(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in title and excerpt"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get total count of published posts (for pagination).
    """
    query = select(func.count(BlogPost.id)).where(BlogPost.status == "published")

    if category:
        query = query.join(BlogCategory).where(BlogCategory.slug == category)

    if tag:
        query = query.where(BlogPost.tags.contains([tag]))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (BlogPost.title.ilike(search_term)) |
            (BlogPost.excerpt.ilike(search_term))
        )

    result = await db.execute(query)
    count = result.scalar()

    return {"count": count}


@router.get("/posts/{slug}", response_model=BlogPostResponse)
async def get_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single published blog post by slug.
    Increments view count.
    """
    result = await db.execute(
        select(BlogPost).where(
            BlogPost.slug == slug,
            BlogPost.status == "published"
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    # Increment view count
    post.view_count = (post.view_count or 0) + 1
    await db.commit()
    await db.refresh(post)

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


@router.get("/categories", response_model=List[BlogCategoryResponse])
async def list_categories(
    include_empty: bool = Query(False, description="Include categories with no published posts"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active blog categories with post counts.
    """
    query = (
        select(BlogCategory)
        .where(BlogCategory.is_active.is_(True))
        .order_by(BlogCategory.display_order, BlogCategory.name)
    )

    result = await db.execute(query)
    categories = result.scalars().all()

    response = []
    for category in categories:
        # Count published posts in this category
        count_query = select(func.count(BlogPost.id)).where(
            BlogPost.category_id == category.id,
            BlogPost.status == "published"
        )
        count_result = await db.execute(count_query)
        post_count = count_result.scalar() or 0

        # Skip empty categories if include_empty is False
        if not include_empty and post_count == 0:
            continue

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


@router.get("/tags")
async def list_tags(
    db: AsyncSession = Depends(get_db),
):
    """
    List all unique tags from published posts with counts.
    """
    # Get all tags from published posts
    result = await db.execute(
        select(BlogPost.tags).where(
            BlogPost.status == "published",
            BlogPost.tags.isnot(None)
        )
    )
    all_tags_lists = result.scalars().all()

    # Flatten and count tags
    tag_counts = {}
    for tags_list in all_tags_lists:
        if tags_list:
            for tag in tags_list:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Sort by count descending
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

    return [{"tag": tag, "count": count} for tag, count in sorted_tags]
