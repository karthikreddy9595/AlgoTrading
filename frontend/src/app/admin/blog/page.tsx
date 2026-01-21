'use client'

import { useState, useEffect } from 'react'
import {
  Plus, Edit, Trash2, Eye, Upload, FileJson,
  CheckCircle, XCircle, Clock, X, ChevronLeft, ChevronRight, Settings
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { BlogPostModal } from './components/BlogPostModal'
import { BulkUploadModal } from './components/BulkUploadModal'
import { CategoryManager } from './components/CategoryManager'
import { BlogPostListItem, BlogCategory } from '@/types/blog'
import { cn } from '@/lib/utils'

const POSTS_PER_PAGE = 10

export default function AdminBlogPage() {
  const [posts, setPosts] = useState<BlogPostListItem[]>([])
  const [categories, setCategories] = useState<BlogCategory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [totalPosts, setTotalPosts] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showPostModal, setShowPostModal] = useState(false)
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [showCategoryManager, setShowCategoryManager] = useState(false)
  const [editingPost, setEditingPost] = useState<BlogPostListItem | null>(null)

  useEffect(() => {
    fetchData()
  }, [currentPage, statusFilter])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const params: any = {
        skip: (currentPage - 1) * POSTS_PER_PAGE,
        limit: POSTS_PER_PAGE,
      }
      if (statusFilter !== 'all') {
        params.status = statusFilter
      }

      const [postsData, countData, categoriesData] = await Promise.all([
        adminApi.getBlogPosts(params),
        adminApi.getBlogPostsCount({ status: statusFilter !== 'all' ? statusFilter : undefined }),
        adminApi.getBlogCategories(true),
      ])

      setPosts(postsData || [])
      setTotalPosts(countData.count)
      setCategories(categoriesData || [])
    } catch (error) {
      toast.error('Failed to load blog data')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this post?')) return
    try {
      await adminApi.deleteBlogPost(id)
      toast.success('Post deleted')
      fetchData()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Delete failed')
    }
  }

  const handlePublish = async (id: string) => {
    try {
      await adminApi.publishBlogPost(id)
      toast.success('Post published')
      fetchData()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Publish failed')
    }
  }

  const handleUnpublish = async (id: string) => {
    try {
      await adminApi.unpublishBlogPost(id)
      toast.success('Post unpublished')
      fetchData()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Unpublish failed')
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return (
          <span className="flex items-center gap-1 text-green-600 text-xs">
            <CheckCircle className="h-3 w-3" /> Published
          </span>
        )
      case 'draft':
        return (
          <span className="flex items-center gap-1 text-yellow-600 text-xs">
            <Clock className="h-3 w-3" /> Draft
          </span>
        )
      case 'archived':
        return (
          <span className="flex items-center gap-1 text-gray-500 text-xs">
            <XCircle className="h-3 w-3" /> Archived
          </span>
        )
      default:
        return status
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const totalPages = Math.ceil(totalPosts / POSTS_PER_PAGE)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Blog Management</h1>
          <p className="text-gray-500">Create and manage blog posts</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowCategoryManager(true)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <Settings className="h-4 w-4" />
            Categories
          </button>
          <button
            onClick={() => setShowBulkModal(true)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <FileJson className="h-4 w-4" />
            Bulk Upload
          </button>
          <button
            onClick={() => {
              setEditingPost(null)
              setShowPostModal(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Post
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'draft', 'published', 'archived'].map((status) => (
          <button
            key={status}
            onClick={() => {
              setStatusFilter(status)
              setCurrentPage(1)
            }}
            className={cn(
              'px-3 py-1.5 text-sm rounded-full capitalize transition-colors',
              statusFilter === status
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
            )}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <div className="text-2xl font-bold">{totalPosts}</div>
          <div className="text-sm text-gray-500">Total Posts</div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <div className="text-2xl font-bold text-green-600">
            {posts.filter(p => p.status === 'published').length}
          </div>
          <div className="text-sm text-gray-500">Published</div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {posts.filter(p => p.status === 'draft').length}
          </div>
          <div className="text-sm text-gray-500">Drafts</div>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <div className="text-2xl font-bold">{categories.length}</div>
          <div className="text-sm text-gray-500">Categories</div>
        </div>
      </div>

      {/* Posts Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            No posts found. Create your first post!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                <tr className="text-left text-sm">
                  <th className="px-6 py-4 font-medium">Title</th>
                  <th className="px-6 py-4 font-medium">Category</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Views</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {posts.map((post) => (
                  <tr key={post.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-6 py-4">
                      <div className="font-medium">{post.title}</div>
                      <div className="text-xs text-gray-500">/blog/{post.slug}</div>
                    </td>
                    <td className="px-6 py-4">
                      {post.category ? (
                        <span
                          className="inline-block text-xs px-2 py-1 rounded"
                          style={{
                            backgroundColor: `${post.category.color}20`,
                            color: post.category.color,
                          }}
                        >
                          {post.category.name}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">None</span>
                      )}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(post.status)}</td>
                    <td className="px-6 py-4 text-sm">{post.view_count}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDate(post.published_at || post.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <a
                          href={`/blog/${post.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-gray-500 hover:text-primary rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                        </a>
                        <button
                          onClick={() => {
                            setEditingPost(post)
                            setShowPostModal(true)
                          }}
                          className="p-2 text-gray-500 hover:text-primary rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                          title="Edit"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        {post.status === 'draft' && (
                          <button
                            onClick={() => handlePublish(post.id)}
                            className="p-2 text-gray-500 hover:text-green-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                            title="Publish"
                          >
                            <CheckCircle className="h-4 w-4" />
                          </button>
                        )}
                        {post.status === 'published' && (
                          <button
                            onClick={() => handleUnpublish(post.id)}
                            className="p-2 text-gray-500 hover:text-yellow-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                            title="Unpublish"
                          >
                            <Clock className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(post.id)}
                          className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-800">
            <div className="text-sm text-gray-500">
              Showing {(currentPage - 1) * POSTS_PER_PAGE + 1} to{' '}
              {Math.min(currentPage * POSTS_PER_PAGE, totalPosts)} of {totalPosts}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showPostModal && (
        <BlogPostModal
          post={editingPost}
          categories={categories}
          onClose={() => {
            setShowPostModal(false)
            setEditingPost(null)
          }}
          onSave={() => {
            fetchData()
            setShowPostModal(false)
            setEditingPost(null)
          }}
        />
      )}

      {showBulkModal && (
        <BulkUploadModal
          onClose={() => setShowBulkModal(false)}
          onSuccess={() => {
            fetchData()
            setShowBulkModal(false)
          }}
        />
      )}

      {showCategoryManager && (
        <CategoryManager
          categories={categories}
          onClose={() => setShowCategoryManager(false)}
          onUpdate={fetchData}
        />
      )}
    </div>
  )
}
