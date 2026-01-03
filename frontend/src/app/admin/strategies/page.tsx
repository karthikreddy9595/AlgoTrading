'use client'

import { useEffect, useState } from 'react'
import {
  BarChart3,
  Plus,
  Edit,
  Trash2,
  Power,
  PowerOff,
  Eye,
  X,
  Star,
  Users,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'
import { toast } from 'sonner'

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
  is_active: boolean
  is_featured: boolean
  created_at: string
}

interface StrategyStats {
  strategy_id: string
  name: string
  total_subscriptions: number
  active_subscriptions: number
  total_capital: number
  total_pnl: number
}

export default function AdminStrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null)
  const [viewingStats, setViewingStats] = useState<StrategyStats | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [includeInactive, setIncludeInactive] = useState(true)

  useEffect(() => {
    fetchStrategies()
  }, [includeInactive])

  const fetchStrategies = async () => {
    setIsLoading(true)
    try {
      const data = await adminApi.getStrategies({ include_inactive: includeInactive })
      setStrategies(data || [])
    } catch (error) {
      console.error('Failed to fetch strategies:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleStatus = async (strategy: Strategy) => {
    setActionLoading(strategy.id)
    try {
      if (strategy.is_active) {
        await adminApi.deleteStrategy(strategy.id)
        toast.success('Strategy deactivated')
      } else {
        await adminApi.activateStrategy(strategy.id)
        toast.success('Strategy activated')
      }
      await fetchStrategies()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Action failed')
    } finally {
      setActionLoading(null)
    }
  }

  const handleViewStats = async (strategyId: string) => {
    try {
      const stats = await adminApi.getStrategyStats(strategyId)
      setViewingStats(stats)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load stats')
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Strategy Management</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage trading strategies
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Create Strategy
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="rounded border-gray-300"
          />
          Show inactive strategies
        </label>
      </div>

      {/* Strategies table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : strategies.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No strategies found
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                  <th className="px-6 py-4 font-medium">Strategy</th>
                  <th className="px-6 py-4 font-medium">Min Capital</th>
                  <th className="px-6 py-4 font-medium">Expected Return</th>
                  <th className="px-6 py-4 font-medium">Max Drawdown</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {strategies.map((strategy) => (
                  <tr key={strategy.id} className="text-sm">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="font-medium">{strategy.name}</div>
                        {strategy.is_featured && (
                          <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        )}
                      </div>
                      <div className="text-xs text-gray-500">{strategy.slug}</div>
                    </td>
                    <td className="px-6 py-4">{formatCurrency(strategy.min_capital)}</td>
                    <td className="px-6 py-4 text-green-600">
                      {strategy.expected_return_percent}%
                    </td>
                    <td className="px-6 py-4 text-red-600">
                      {strategy.max_drawdown_percent}%
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        'px-2 py-1 text-xs rounded',
                        strategy.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                      )}>
                        {strategy.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewStats(strategy.id)}
                          title="View stats"
                          className="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setEditingStrategy(strategy)}
                          title="Edit strategy"
                          className="p-2 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleToggleStatus(strategy)}
                          disabled={actionLoading === strategy.id}
                          title={strategy.is_active ? 'Deactivate' : 'Activate'}
                          className={cn(
                            'p-2 rounded-lg disabled:opacity-50',
                            strategy.is_active
                              ? 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                              : 'text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
                          )}
                        >
                          {actionLoading === strategy.id ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                          ) : strategy.is_active ? (
                            <PowerOff className="h-4 w-4" />
                          ) : (
                            <Power className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingStrategy) && (
        <StrategyModal
          strategy={editingStrategy}
          onClose={() => {
            setShowCreateModal(false)
            setEditingStrategy(null)
          }}
          onSave={async () => {
            await fetchStrategies()
            setShowCreateModal(false)
            setEditingStrategy(null)
          }}
        />
      )}

      {/* Stats Modal */}
      {viewingStats && (
        <StatsModal
          stats={viewingStats}
          onClose={() => setViewingStats(null)}
        />
      )}
    </div>
  )
}

function StrategyModal({
  strategy,
  onClose,
  onSave,
}: {
  strategy: Strategy | null
  onClose: () => void
  onSave: () => void
}) {
  const [formData, setFormData] = useState({
    name: strategy?.name || '',
    slug: strategy?.slug || '',
    description: strategy?.description || '',
    min_capital: strategy?.min_capital || 10000,
    expected_return_percent: strategy?.expected_return_percent || 0,
    max_drawdown_percent: strategy?.max_drawdown_percent || 0,
    timeframe: strategy?.timeframe || '',
    module_path: '',
    class_name: '',
    is_featured: strategy?.is_featured || false,
  })
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      if (strategy) {
        await adminApi.updateStrategy(strategy.id, {
          name: formData.name,
          description: formData.description,
          min_capital: formData.min_capital,
          expected_return_percent: formData.expected_return_percent,
          max_drawdown_percent: formData.max_drawdown_percent,
          is_featured: formData.is_featured,
        })
        toast.success('Strategy updated')
      } else {
        await adminApi.createStrategy({
          ...formData,
        })
        toast.success('Strategy created')
      }
      onSave()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save strategy')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold">
            {strategy ? 'Edit Strategy' : 'Create Strategy'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              required
            />
          </div>
          {!strategy && (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">Slug</label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Module Path</label>
                <input
                  type="text"
                  value={formData.module_path}
                  onChange={(e) => setFormData({ ...formData, module_path: e.target.value })}
                  placeholder="strategies.implementations.my_strategy"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Class Name</label>
                <input
                  type="text"
                  value={formData.class_name}
                  onChange={(e) => setFormData({ ...formData, class_name: e.target.value })}
                  placeholder="MyStrategy"
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                  required
                />
              </div>
            </>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              rows={3}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Min Capital</label>
              <input
                type="number"
                value={formData.min_capital}
                onChange={(e) => setFormData({ ...formData, min_capital: Number(e.target.value) })}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Timeframe</label>
              <input
                type="text"
                value={formData.timeframe}
                onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                placeholder="5min"
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Expected Return %</label>
              <input
                type="number"
                step="0.01"
                value={formData.expected_return_percent}
                onChange={(e) => setFormData({ ...formData, expected_return_percent: Number(e.target.value) })}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Drawdown %</label>
              <input
                type="number"
                step="0.01"
                value={formData.max_drawdown_percent}
                onChange={(e) => setFormData({ ...formData, max_drawdown_percent: Number(e.target.value) })}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_featured"
              checked={formData.is_featured}
              onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="is_featured" className="text-sm">Featured strategy</label>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : strategy ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function StatsModal({
  stats,
  onClose,
}: {
  stats: StrategyStats
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold">{stats.name} - Stats</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">Total Subscriptions</div>
              <div className="text-2xl font-bold">{stats.total_subscriptions}</div>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">Active</div>
              <div className="text-2xl font-bold text-green-600">{stats.active_subscriptions}</div>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">Total Capital</div>
              <div className="text-2xl font-bold">{formatCurrency(stats.total_capital)}</div>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-sm text-gray-500 dark:text-gray-400">Total P&L</div>
              <div className={cn(
                'text-2xl font-bold',
                stats.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'
              )}>
                {formatCurrency(stats.total_pnl)}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
