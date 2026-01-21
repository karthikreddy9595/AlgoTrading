"""Add blog tables for categories and posts

Revision ID: 005
Revises: 004
Create Date: 2024-01-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Blog Categories table
    op.create_table(
        'blog_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), server_default="'#6366f1'"),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('idx_blog_categories_slug', 'blog_categories', ['slug'])
    op.create_index('idx_blog_categories_active', 'blog_categories', ['is_active'])

    # Blog Posts table
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        # Core content
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('excerpt', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        # Media
        sa.Column('featured_image', sa.String(500), nullable=True),
        sa.Column('featured_image_alt', sa.String(255), nullable=True),
        # Organization
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blog_categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        # Metadata
        sa.Column('author_name', sa.String(255), server_default="'ArthaQuant Team'"),
        sa.Column('reading_time_minutes', sa.Integer(), server_default='5'),
        # SEO fields
        sa.Column('meta_title', sa.String(70), nullable=True),
        sa.Column('meta_description', sa.String(160), nullable=True),
        sa.Column('meta_keywords', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('canonical_url', sa.String(500), nullable=True),
        # Publishing workflow
        sa.Column('status', sa.String(20), server_default="'draft'"),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        # Analytics
        sa.Column('view_count', sa.Integer(), server_default='0'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        # Created by (admin user)
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('idx_blog_posts_slug', 'blog_posts', ['slug'])
    op.create_index('idx_blog_posts_status', 'blog_posts', ['status'])
    op.create_index('idx_blog_posts_published', 'blog_posts', ['published_at'])
    op.create_index('idx_blog_posts_category', 'blog_posts', ['category_id'])
    op.create_index('idx_blog_posts_created', 'blog_posts', ['created_at'])


def downgrade() -> None:
    op.drop_table('blog_posts')
    op.drop_table('blog_categories')
