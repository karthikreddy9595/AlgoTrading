'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Search, Filter, TrendingUp, Clock, DollarSign, Star } from 'lucide-react'
import { strategyApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'

interface Strategy {
  id: string
  name: string
  slug: string
  description: string
  version: string
  min_capital: number
  expected_return_percent: number
  max_drawdown_percent: number
  timeframe: string
  tags: string[]
  is_featured: boolean
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const data = await strategyApi.list()
        setStrategies(data)
      } catch (error) {
        console.error('Failed to fetch strategies:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchStrategies()
  }, [])

  const filteredStrategies = strategies.filter((strategy) => {
    const matchesSearch =
      strategy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      strategy.description?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = !selectedTag || strategy.tags?.includes(selectedTag)
    return matchesSearch && matchesTag
  })

  const allTags = [...new Set(strategies.flatMap((s) => s.tags || []))]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Strategies</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Browse and subscribe to trading strategies
        </p>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search strategies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
          <button
            onClick={() => setSelectedTag(null)}
            className={cn(
              'px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
              !selectedTag
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            )}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag)}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                selectedTag === tag
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Strategies grid */}
      {filteredStrategies.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            {strategies.length === 0
              ? 'No strategies available yet'
              : 'No strategies match your search'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStrategies.map((strategy) => (
            <StrategyCard key={strategy.id} strategy={strategy} />
          ))}
        </div>
      )}
    </div>
  )
}

function StrategyCard({ strategy }: { strategy: Strategy }) {
  return (
    <Link
      href={`/dashboard/strategies/${strategy.slug}`}
      className="block bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 hover:border-primary dark:hover:border-primary transition-colors overflow-hidden"
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold">{strategy.name}</h3>
              {strategy.is_featured && (
                <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              v{strategy.version}
            </p>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-green-600">
              {strategy.expected_return_percent
                ? formatPercent(strategy.expected_return_percent)
                : 'N/A'}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Expected Return
            </p>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-2">
          {strategy.description || 'No description available'}
        </p>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <DollarSign className="h-5 w-5 mx-auto mb-1 text-gray-400" />
            <p className="text-sm font-medium">
              {formatCurrency(strategy.min_capital)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Min Capital</p>
          </div>
          <div className="text-center">
            <TrendingUp className="h-5 w-5 mx-auto mb-1 text-gray-400" />
            <p className="text-sm font-medium text-red-600">
              {strategy.max_drawdown_percent
                ? `-${strategy.max_drawdown_percent}%`
                : 'N/A'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Max DD</p>
          </div>
          <div className="text-center">
            <Clock className="h-5 w-5 mx-auto mb-1 text-gray-400" />
            <p className="text-sm font-medium">{strategy.timeframe || 'N/A'}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Timeframe</p>
          </div>
        </div>

        {/* Tags */}
        {strategy.tags && strategy.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {strategy.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-800">
        <span className="text-sm font-medium text-primary">
          View Details →
        </span>
      </div>
    </Link>
  )
}
