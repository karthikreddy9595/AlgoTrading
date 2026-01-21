'use client'

import { useState, useEffect } from 'react'
import { Metadata } from 'next'
import Link from 'next/link'
import Image from 'next/image'
import { Search, Calendar, Clock, User, Tag, ChevronLeft, ChevronRight } from 'lucide-react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { blogApi } from '@/lib/api'
import { BlogPostListItem, BlogCategory, BlogTag } from '@/types/blog'

const POSTS_PER_PAGE = 9

export default function BlogPage() {
  const [posts, setPosts] = useState<BlogPostListItem[]>([])
  const [categories, setCategories] = useState<BlogCategory[]>([])
  const [tags, setTags] = useState<BlogTag[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [totalPosts, setTotalPosts] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchData()
  }, [currentPage, selectedCategory, selectedTag])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const [postsData, countData, categoriesData, tagsData] = await Promise.all([
        blogApi.getPosts({
          skip: (currentPage - 1) * POSTS_PER_PAGE,
          limit: POSTS_PER_PAGE,
          category: selectedCategory || undefined,
          tag: selectedTag || undefined,
          search: searchQuery || undefined,
        }),
        blogApi.getPostsCount({
          category: selectedCategory || undefined,
          tag: selectedTag || undefined,
          search: searchQuery || undefined,
        }),
        blogApi.getCategories(),
        blogApi.getTags(),
      ])
      setPosts(postsData)
      setTotalPosts(countData.count)
      setCategories(categoriesData)
      setTags(tagsData)
    } catch (error) {
      console.error('Failed to fetch blog data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
    fetchData()
  }

  const handleCategoryClick = (slug: string | null) => {
    setSelectedCategory(slug)
    setSelectedTag(null)
    setCurrentPage(1)
  }

  const handleTagClick = (tag: string | null) => {
    setSelectedTag(tag)
    setSelectedCategory(null)
    setCurrentPage(1)
  }

  const totalPages = Math.ceil(totalPosts / POSTS_PER_PAGE)

  const formatDate = (dateString: string | null) => {
    if (!dateString) return ''
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <Header />

      {/* Hero with Cover Image */}
      <section className="relative overflow-hidden">
        {/* Background Image */}
        <div className="absolute inset-0">
          <img
            src="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80"
            alt="Trading background"
            className="w-full h-full object-cover"
          />
          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-gray-900/95 via-gray-900/80 to-gray-900/70" />
          {/* Decorative Elements */}
          <div className="absolute inset-0 opacity-30">
            <div className="absolute top-10 left-10 w-72 h-72 bg-primary/30 rounded-full blur-3xl" />
            <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
          </div>
        </div>

        {/* Content */}
        <div className="relative container mx-auto px-4 py-20 md:py-28">
          <div className="max-w-3xl">
            <span className="inline-block px-4 py-1 bg-primary/20 text-primary rounded-full text-sm font-medium mb-4">
              ArthaQuant Blog
            </span>
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Insights & Strategies for
              <span className="text-primary"> Smarter Trading</span>
            </h1>
            <p className="text-xl text-gray-300 max-w-2xl">
              Explore expert insights on algorithmic trading, learn proven strategies,
              understand market dynamics, and stay updated with the latest in automated trading.
            </p>

            {/* Stats */}
            <div className="flex flex-wrap gap-8 mt-8">
              <div>
                <p className="text-3xl font-bold text-white">{totalPosts}+</p>
                <p className="text-gray-400 text-sm">Articles</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">{categories.length}</p>
                <p className="text-gray-400 text-sm">Categories</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">{tags.length}+</p>
                <p className="text-gray-400 text-sm">Topics</p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Wave */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg
            viewBox="0 0 1440 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-full h-auto"
          >
            <path
              d="M0 120L60 105C120 90 240 60 360 45C480 30 600 30 720 37.5C840 45 960 60 1080 67.5C1200 75 1320 75 1380 75L1440 75V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
              className="fill-white dark:fill-gray-950"
            />
          </svg>
        </div>
      </section>

      <div className="container mx-auto px-4 py-12">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Content */}
          <div className="flex-1">
            {/* Search */}
            <form onSubmit={handleSearch} className="mb-8">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search articles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </form>

            {/* Active Filters */}
            {(selectedCategory || selectedTag) && (
              <div className="flex items-center gap-2 mb-6">
                <span className="text-sm text-gray-500">Filtered by:</span>
                {selectedCategory && (
                  <button
                    onClick={() => handleCategoryClick(null)}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                  >
                    {categories.find(c => c.slug === selectedCategory)?.name}
                    <span className="ml-1">&times;</span>
                  </button>
                )}
                {selectedTag && (
                  <button
                    onClick={() => handleTagClick(null)}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                  >
                    {selectedTag}
                    <span className="ml-1">&times;</span>
                  </button>
                )}
              </div>
            )}

            {/* Posts Grid */}
            {isLoading ? (
              <div className="flex items-center justify-center py-20">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              </div>
            ) : posts.length === 0 ? (
              <div className="text-center py-20">
                <p className="text-gray-500">No articles found. Check back later!</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {posts.map((post) => (
                  <BlogCard key={post.id} post={post} formatDate={formatDate} />
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-12">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="px-4 py-2 text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="lg:w-80">
            {/* Categories */}
            <div className="mb-8">
              <h3 className="font-semibold mb-4">Categories</h3>
              <div className="space-y-2">
                <button
                  onClick={() => handleCategoryClick(null)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    !selectedCategory
                      ? 'bg-primary text-white'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  All Categories
                </button>
                {categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => handleCategoryClick(category.slug)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between ${
                      selectedCategory === category.slug
                        ? 'bg-primary text-white'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                      {category.name}
                    </span>
                    {category.post_count !== undefined && (
                      <span className="text-xs opacity-70">{category.post_count}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Tags */}
            {tags.length > 0 && (
              <div>
                <h3 className="font-semibold mb-4">Popular Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {tags.slice(0, 15).map((tagItem) => (
                    <button
                      key={tagItem.tag}
                      onClick={() => handleTagClick(selectedTag === tagItem.tag ? null : tagItem.tag)}
                      className={`px-3 py-1 rounded-full text-sm transition-colors ${
                        selectedTag === tagItem.tag
                          ? 'bg-primary text-white'
                          : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                      }`}
                    >
                      {tagItem.tag}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      </div>

      <Footer />
    </div>
  )
}

function BlogCard({
  post,
  formatDate,
}: {
  post: BlogPostListItem
  formatDate: (date: string | null) => string
}) {
  return (
    <Link href={`/blog/${post.slug}`} className="group">
      <article className="h-full rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden hover:shadow-lg transition-shadow bg-white dark:bg-gray-900">
        {post.featured_image && (
          <div className="aspect-video relative overflow-hidden bg-gray-100 dark:bg-gray-800">
            <img
              src={post.featured_image}
              alt={post.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          </div>
        )}
        <div className="p-5">
          {post.category && (
            <span
              className="inline-block text-xs font-medium px-2 py-1 rounded mb-3"
              style={{
                backgroundColor: `${post.category.color}20`,
                color: post.category.color,
              }}
            >
              {post.category.name}
            </span>
          )}
          <h2 className="text-lg font-semibold mb-2 group-hover:text-primary transition-colors line-clamp-2">
            {post.title}
          </h2>
          {post.excerpt && (
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
              {post.excerpt}
            </p>
          )}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              {post.author_name}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {post.reading_time_minutes} min
            </span>
          </div>
          {post.published_at && (
            <p className="text-xs text-gray-400 mt-2">
              {formatDate(post.published_at)}
            </p>
          )}
        </div>
      </article>
    </Link>
  )
}
