'use client'

import { useState, useEffect } from 'react'
import { X, Upload, Image as ImageIcon } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { BlogPostListItem, BlogCategory } from '@/types/blog'

interface BlogPostModalProps {
  post: BlogPostListItem | null
  categories: BlogCategory[]
  onClose: () => void
  onSave: () => void
}

export function BlogPostModal({ post, categories, onClose, onSave }: BlogPostModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [fullPost, setFullPost] = useState<any>(null)
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    excerpt: '',
    content: '',
    featured_image: '',
    featured_image_alt: '',
    category_id: '',
    tags: '',
    author_name: 'ArthaQuant Team',
    reading_time_minutes: 5,
    meta_title: '',
    meta_description: '',
    status: 'draft',
  })

  const isEditing = !!post

  useEffect(() => {
    if (post) {
      // Fetch full post data for editing
      fetchFullPost(post.id)
    }
  }, [post])

  const fetchFullPost = async (id: string) => {
    try {
      const data = await adminApi.getBlogPost(id)
      setFullPost(data)
      setFormData({
        title: data.title || '',
        slug: data.slug || '',
        excerpt: data.excerpt || '',
        content: data.content || '',
        featured_image: data.featured_image || '',
        featured_image_alt: data.featured_image_alt || '',
        category_id: data.category_id || '',
        tags: data.tags ? data.tags.join(', ') : '',
        author_name: data.author_name || 'ArthaQuant Team',
        reading_time_minutes: data.reading_time_minutes || 5,
        meta_title: data.meta_title || '',
        meta_description: data.meta_description || '',
        status: data.status || 'draft',
      })
    } catch (error) {
      toast.error('Failed to load post')
    }
  }

  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
  }

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const title = e.target.value
    setFormData((prev) => ({
      ...prev,
      title,
      slug: isEditing ? prev.slug : generateSlug(title),
    }))
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      const result = await adminApi.uploadBlogImage(file)
      setFormData((prev) => ({
        ...prev,
        featured_image: result.path,
      }))
      toast.success('Image uploaded')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const payload = {
        title: formData.title,
        slug: formData.slug,
        excerpt: formData.excerpt || undefined,
        content: formData.content,
        featured_image: formData.featured_image || undefined,
        featured_image_alt: formData.featured_image_alt || undefined,
        category_id: formData.category_id || undefined,
        tags: formData.tags ? formData.tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
        author_name: formData.author_name,
        reading_time_minutes: formData.reading_time_minutes,
        meta_title: formData.meta_title || undefined,
        meta_description: formData.meta_description || undefined,
        status: formData.status,
      }

      if (isEditing && post) {
        await adminApi.updateBlogPost(post.id, payload)
        toast.success('Post updated')
      } else {
        await adminApi.createBlogPost(payload)
        toast.success('Post created')
      }

      onSave()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Save failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4">
      <div className="w-full max-w-4xl bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold">
            {isEditing ? 'Edit Post' : 'Create New Post'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Title & Slug */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={handleTitleChange}
                required
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                placeholder="Post title"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Slug *</label>
              <input
                type="text"
                value={formData.slug}
                onChange={(e) => setFormData((prev) => ({ ...prev, slug: e.target.value }))}
                required
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                placeholder="post-url-slug"
              />
            </div>
          </div>

          {/* Excerpt */}
          <div>
            <label className="block text-sm font-medium mb-2">Excerpt</label>
            <textarea
              value={formData.excerpt}
              onChange={(e) => setFormData((prev) => ({ ...prev, excerpt: e.target.value }))}
              rows={2}
              maxLength={500}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              placeholder="Brief summary for blog cards"
            />
            <p className="text-xs text-gray-500 mt-1">{formData.excerpt.length}/500</p>
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-medium mb-2">Content (Markdown) *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData((prev) => ({ ...prev, content: e.target.value }))}
              required
              rows={15}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 font-mono text-sm"
              placeholder="# Your Article Title

Write your content in Markdown format...

## Section Heading

- List item 1
- List item 2

```python
# Code blocks are supported
print('Hello World')
```"
            />
          </div>

          {/* Featured Image */}
          <div>
            <label className="block text-sm font-medium mb-2">Featured Image</label>
            <div className="flex items-center gap-4">
              {formData.featured_image ? (
                <div className="relative">
                  <img
                    src={formData.featured_image}
                    alt="Featured"
                    className="w-32 h-20 object-cover rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, featured_image: '' }))}
                    className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <div className="w-32 h-20 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg flex items-center justify-center">
                  <ImageIcon className="h-8 w-8 text-gray-400" />
                </div>
              )}
              <div>
                <label className="flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                  <Upload className="h-4 w-4" />
                  {isUploading ? 'Uploading...' : 'Upload Image'}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                </label>
                <p className="text-xs text-gray-500 mt-1">JPG, PNG, GIF, WebP. Max 5MB.</p>
              </div>
            </div>
            {formData.featured_image && (
              <input
                type="text"
                value={formData.featured_image_alt}
                onChange={(e) => setFormData((prev) => ({ ...prev, featured_image_alt: e.target.value }))}
                className="w-full mt-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                placeholder="Image alt text"
              />
            )}
          </div>

          {/* Category & Tags */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Category</label>
              <select
                value={formData.category_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, category_id: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <option value="">No category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Tags</label>
              <input
                type="text"
                value={formData.tags}
                onChange={(e) => setFormData((prev) => ({ ...prev, tags: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                placeholder="trading, strategy, beginner (comma separated)"
              />
            </div>
          </div>

          {/* Author & Reading Time */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Author</label>
              <input
                type="text"
                value={formData.author_name}
                onChange={(e) => setFormData((prev) => ({ ...prev, author_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Reading Time (minutes)</label>
              <input
                type="number"
                min="1"
                max="120"
                value={formData.reading_time_minutes}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, reading_time_minutes: parseInt(e.target.value) || 5 }))
                }
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
          </div>

          {/* SEO */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="font-medium mb-4">SEO Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Meta Title <span className="text-gray-400">(max 70 chars)</span>
                </label>
                <input
                  type="text"
                  value={formData.meta_title}
                  onChange={(e) => setFormData((prev) => ({ ...prev, meta_title: e.target.value }))}
                  maxLength={70}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  placeholder="Leave blank to use post title"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Meta Description <span className="text-gray-400">(max 160 chars)</span>
                </label>
                <textarea
                  value={formData.meta_description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, meta_description: e.target.value }))}
                  maxLength={160}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  placeholder="Leave blank to use excerpt"
                />
              </div>
            </div>
          </div>

          {/* Status & Submit */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="block text-sm font-medium mb-2">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData((prev) => ({ ...prev, status: e.target.value }))}
                className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : isEditing ? 'Update Post' : 'Create Post'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
