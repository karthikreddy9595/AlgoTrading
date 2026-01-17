'use client'

import { useState, useEffect } from 'react'
import { Loader2, Trophy, ChevronUp, ChevronDown, TrendingUp, TrendingDown } from 'lucide-react'
import { optimizationApi } from '@/lib/api'
import { OptimizationResults as OptimizationResultsType, OptimizationResultItem } from '@/types/optimization'
import { ParameterHeatmap } from './ParameterHeatmap'
import { formatCurrency, cn } from '@/lib/utils'

interface OptimizationResultsProps {
  optimizationId: string
  initialCapital: number
}

type SortField = 'total_return_percent' | 'sharpe_ratio' | 'max_drawdown' | 'win_rate' | 'profit_factor' | 'total_trades'
type SortDirection = 'asc' | 'desc'

export function OptimizationResults({ optimizationId, initialCapital }: OptimizationResultsProps) {
  const [results, setResults] = useState<OptimizationResultsType | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<SortField>('total_return_percent')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    fetchResults()
  }, [optimizationId])

  const fetchResults = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await optimizationApi.getResults(optimizationId)
      setResults(data)
    } catch (err: any) {
      console.error('Failed to fetch optimization results:', err)
      setError(err.response?.data?.detail || 'Failed to load results')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const sortedResults = results?.all_results
    ? [...results.all_results].sort((a, b) => {
        const aVal = a[sortField] ?? 0
        const bVal = b[sortField] ?? 0
        return sortDirection === 'asc' ? Number(aVal) - Number(bVal) : Number(bVal) - Number(aVal)
      })
    : []

  const displayedResults = showAll ? sortedResults : sortedResults.slice(0, 10)

  const parameterNames = results?.best_result
    ? Object.keys(results.best_result.parameters)
    : []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={fetchResults} className="px-4 py-2 bg-primary text-white rounded-lg">
          Retry
        </button>
      </div>
    )
  }

  if (!results) return null

  return (
    <div className="space-y-6">
      {/* Best Result Card */}
      {results.best_result && (
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border border-green-200 dark:border-green-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-100 dark:bg-green-900/40 rounded-full">
              <Trophy className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-200">
                Best Parameters Found
              </h3>
              <p className="text-sm text-green-600 dark:text-green-400">
                Optimized for {results.objective_metric.replace(/_/g, ' ')}
              </p>
            </div>
          </div>

          {/* Best Parameters */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {Object.entries(results.best_result.parameters).map(([name, value]) => (
              <div key={name} className="bg-white dark:bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-0.5">{name}</p>
                <p className="font-semibold">{value}</p>
              </div>
            ))}
          </div>

          {/* Best Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard
              label="Total Return"
              value={`${Number(results.best_result.total_return_percent ?? 0).toFixed(2)}%`}
              isPositive={Number(results.best_result.total_return_percent ?? 0) > 0}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={Number(results.best_result.sharpe_ratio ?? 0).toFixed(2)}
              isPositive={Number(results.best_result.sharpe_ratio ?? 0) > 1}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${Number(results.best_result.max_drawdown ?? 0).toFixed(2)}%`}
              isPositive={false}
              isNegativeMetric
            />
            <MetricCard
              label="Win Rate"
              value={`${Number(results.best_result.win_rate ?? 0).toFixed(1)}%`}
              isPositive={Number(results.best_result.win_rate ?? 0) > 50}
            />
            <MetricCard
              label="Trades"
              value={results.best_result.total_trades.toString()}
            />
          </div>
        </div>
      )}

      {/* Heatmap */}
      {parameterNames.length >= 2 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4">Parameter Sensitivity Heatmap</h3>
          <ParameterHeatmap
            optimizationId={optimizationId}
            parameters={parameterNames}
            objectiveMetric={results.objective_metric}
          />
        </div>
      )}

      {/* Results Table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">All Results ({results.total_samples} samples)</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-2 font-medium text-gray-500">Rank</th>
                <th className="text-left py-3 px-2 font-medium text-gray-500">Parameters</th>
                <SortableHeader
                  label="Return %"
                  field="total_return_percent"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Sharpe"
                  field="sharpe_ratio"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Max DD"
                  field="max_drawdown"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Win Rate"
                  field="win_rate"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Profit F"
                  field="profit_factor"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Trades"
                  field="total_trades"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                />
              </tr>
            </thead>
            <tbody>
              {displayedResults.map((result, index) => (
                <tr
                  key={result.id}
                  className={cn(
                    'border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50',
                    result.is_best && 'bg-green-50 dark:bg-green-900/20'
                  )}
                >
                  <td className="py-3 px-2">
                    {result.is_best ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded text-xs font-medium">
                        <Trophy className="h-3 w-3" />
                        Best
                      </span>
                    ) : (
                      <span className="text-gray-500">#{index + 1}</span>
                    )}
                  </td>
                  <td className="py-3 px-2">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(result.parameters).map(([name, value]) => (
                        <span
                          key={name}
                          className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs"
                        >
                          {name}: {value}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-2">
                    <span
                      className={cn(
                        'font-medium',
                        Number(result.total_return_percent ?? 0) > 0 ? 'text-green-600' : 'text-red-600'
                      )}
                    >
                      {Number(result.total_return_percent ?? 0).toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-3 px-2">{Number(result.sharpe_ratio ?? 0).toFixed(2)}</td>
                  <td className="py-3 px-2 text-red-600">
                    {Number(result.max_drawdown ?? 0).toFixed(2)}%
                  </td>
                  <td className="py-3 px-2">{Number(result.win_rate ?? 0).toFixed(1)}%</td>
                  <td className="py-3 px-2">{Number(result.profit_factor ?? 0).toFixed(2)}</td>
                  <td className="py-3 px-2">{result.total_trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Show More/Less */}
        {sortedResults.length > 10 && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm text-primary hover:underline"
            >
              {showAll ? 'Show Less' : `Show All ${sortedResults.length} Results`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  isPositive,
  isNegativeMetric = false,
}: {
  label: string
  value: string
  isPositive?: boolean
  isNegativeMetric?: boolean
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p
        className={cn(
          'font-semibold',
          isPositive !== undefined &&
            (isPositive
              ? 'text-green-600 dark:text-green-400'
              : isNegativeMetric
              ? 'text-red-600 dark:text-red-400'
              : '')
        )}
      >
        {value}
      </p>
    </div>
  )
}

function SortableHeader({
  label,
  field,
  currentField,
  direction,
  onSort,
}: {
  label: string
  field: SortField
  currentField: SortField
  direction: SortDirection
  onSort: (field: SortField) => void
}) {
  const isActive = currentField === field

  return (
    <th
      className="text-left py-3 px-2 font-medium text-gray-500 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {isActive && (direction === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
      </div>
    </th>
  )
}
