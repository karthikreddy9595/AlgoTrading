'use client'

import { useState } from 'react'
import { X, Upload, FileJson, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { BlogPostBulkResult } from '@/types/blog'

interface BulkUploadModalProps {
  onClose: () => void
  onSuccess: () => void
}

const EXAMPLE_JSON = `{
  "posts": [
    {
      "title": "Introduction to Algorithmic Trading",
      "slug": "introduction-to-algorithmic-trading",
      "excerpt": "Learn the fundamentals of algorithmic trading...",
      "content": "# Introduction\\n\\nAlgorithmic trading uses computer programs...",
      "category_slug": "trading-basics",
      "tags": ["algorithmic-trading", "beginners"],
      "author_name": "ArthaQuant Team",
      "reading_time_minutes": 8,
      "meta_title": "Intro to Algo Trading | ArthaQuant",
      "meta_description": "Discover the fundamentals...",
      "status": "draft"
    }
  ]
}`

export function BulkUploadModal({ onClose, onSuccess }: BulkUploadModalProps) {
  const [jsonContent, setJsonContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<BlogPostBulkResult | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result as string
      setJsonContent(content)
      validateJson(content)
    }
    reader.readAsText(file)
  }

  const validateJson = (content: string): boolean => {
    setParseError(null)
    try {
      const data = JSON.parse(content)
      if (!data.posts || !Array.isArray(data.posts)) {
        setParseError('JSON must have a "posts" array')
        return false
      }
      if (data.posts.length === 0) {
        setParseError('Posts array is empty')
        return false
      }
      for (let i = 0; i < data.posts.length; i++) {
        const post = data.posts[i]
        if (!post.title || !post.slug || !post.content) {
          setParseError(`Post at index ${i} is missing required fields (title, slug, content)`)
          return false
        }
      }
      return true
    } catch (e: any) {
      setParseError(`Invalid JSON: ${e.message}`)
      return false
    }
  }

  const handleSubmit = async () => {
    if (!validateJson(jsonContent)) return

    setIsLoading(true)
    setResult(null)

    try {
      const data = JSON.parse(jsonContent)
      const result = await adminApi.bulkUploadBlogPosts(data)
      setResult(result)

      if (result.created > 0) {
        toast.success(`${result.created} posts created successfully`)
      }
      if (result.failed > 0) {
        toast.warning(`${result.failed} posts failed`)
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Bulk upload failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    if (result && result.created > 0) {
      onSuccess()
    } else {
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 p-4">
      <div className="w-full max-w-3xl bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <FileJson className="h-6 w-6 text-primary" />
            <h2 className="text-xl font-semibold">Bulk Upload Posts</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Instructions */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
              JSON Format Instructions
            </h3>
            <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
              <li>Upload a JSON file or paste JSON content below</li>
              <li>Required fields: <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">title</code>, <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">slug</code>, <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">content</code></li>
              <li>Use <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">category_slug</code> to assign a category (must exist)</li>
              <li>Content should be in Markdown format</li>
            </ul>
          </div>

          {/* File Upload */}
          <div>
            <label className="flex items-center justify-center gap-2 w-full p-8 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary transition-colors">
              <Upload className="h-6 w-6 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">
                Drop JSON file here or click to upload
              </span>
              <input
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>

          {/* JSON Editor */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">JSON Content</label>
              <button
                type="button"
                onClick={() => setJsonContent(EXAMPLE_JSON)}
                className="text-xs text-primary hover:underline"
              >
                Load Example
              </button>
            </div>
            <textarea
              value={jsonContent}
              onChange={(e) => {
                setJsonContent(e.target.value)
                if (e.target.value) validateJson(e.target.value)
              }}
              rows={12}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 font-mono text-sm"
              placeholder="Paste your JSON here..."
            />
            {parseError && (
              <div className="flex items-center gap-2 mt-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                {parseError}
              </div>
            )}
          </div>

          {/* Result */}
          {result && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <h3 className="font-medium mb-3">Upload Result</h3>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">{result.total}</div>
                  <div className="text-sm text-gray-500">Total</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{result.created}</div>
                  <div className="text-sm text-gray-500">Created</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{result.failed}</div>
                  <div className="text-sm text-gray-500">Failed</div>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2 text-red-600">Errors:</h4>
                  <ul className="space-y-1 text-sm">
                    {result.errors.map((err, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-red-600">
                        <XCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <span>
                          Post #{err.index} ({err.slug}): {err.error}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-800">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {result ? 'Close' : 'Cancel'}
          </button>
          {!result && (
            <button
              onClick={handleSubmit}
              disabled={isLoading || !jsonContent || !!parseError}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoading ? 'Uploading...' : 'Upload Posts'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
