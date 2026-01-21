export interface BlogCategory {
  id: string
  name: string
  slug: string
  description: string | null
  color: string
  is_active: boolean
  display_order: number
  post_count?: number
  created_at: string
}

export interface BlogPost {
  id: string
  title: string
  slug: string
  excerpt: string | null
  content: string
  featured_image: string | null
  featured_image_alt: string | null
  category_id: string | null
  category: BlogCategory | null
  tags: string[] | null
  author_name: string
  reading_time_minutes: number
  meta_title: string | null
  meta_description: string | null
  meta_keywords: string[] | null
  canonical_url: string | null
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  view_count: number
  created_at: string
  updated_at: string
}

export interface BlogPostListItem {
  id: string
  title: string
  slug: string
  excerpt: string | null
  featured_image: string | null
  category: BlogCategory | null
  tags: string[] | null
  author_name: string
  reading_time_minutes: number
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  view_count: number
  created_at: string
}

export interface BlogPostCreate {
  title: string
  slug: string
  excerpt?: string
  content: string
  featured_image?: string
  featured_image_alt?: string
  category_id?: string
  tags?: string[]
  author_name?: string
  reading_time_minutes?: number
  meta_title?: string
  meta_description?: string
  meta_keywords?: string[]
  canonical_url?: string
  status?: 'draft' | 'published'
}

export interface BlogPostUpdate {
  title?: string
  slug?: string
  excerpt?: string
  content?: string
  featured_image?: string
  featured_image_alt?: string
  category_id?: string
  tags?: string[]
  author_name?: string
  reading_time_minutes?: number
  meta_title?: string
  meta_description?: string
  meta_keywords?: string[]
  canonical_url?: string
  status?: 'draft' | 'published' | 'archived'
}

export interface BlogCategoryCreate {
  name: string
  slug: string
  description?: string
  color?: string
  display_order?: number
}

export interface BlogCategoryUpdate {
  name?: string
  slug?: string
  description?: string
  color?: string
  is_active?: boolean
  display_order?: number
}

export interface BlogPostBulkItem {
  title: string
  slug: string
  excerpt?: string
  content: string
  featured_image?: string
  featured_image_alt?: string
  category_slug?: string
  tags?: string[]
  author_name?: string
  reading_time_minutes?: number
  meta_title?: string
  meta_description?: string
  meta_keywords?: string[]
  status?: 'draft' | 'published'
}

export interface BlogPostBulkUpload {
  posts: BlogPostBulkItem[]
}

export interface BlogPostBulkResult {
  total: number
  created: number
  failed: number
  errors: Array<{
    index: number
    slug: string
    error: string
  }>
}

export interface BlogTag {
  tag: string
  count: number
}
