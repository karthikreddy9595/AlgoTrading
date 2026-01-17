'use client'

import { useState, useEffect, useMemo } from 'react'
import { Loader2 } from 'lucide-react'
import { optimizationApi } from '@/lib/api'
import { HeatmapData } from '@/types/optimization'

interface ParameterHeatmapProps {
  optimizationId: string
  parameters: string[]
  objectiveMetric: string
}

const METRICS = [
  { value: 'total_return_percent', label: 'Total Return %' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'sortino_ratio', label: 'Sortino Ratio' },
  { value: 'profit_factor', label: 'Profit Factor' },
  { value: 'win_rate', label: 'Win Rate' },
  { value: 'max_drawdown', label: 'Max Drawdown' },
]

// Color interpolation function
function interpolateColor(value: number, min: number, max: number): string {
  // Normalize value to 0-1 range
  const normalized = max === min ? 0.5 : (value - min) / (max - min)

  // Use a gradient from red -> yellow -> green
  if (normalized <= 0.5) {
    // Red to Yellow
    const t = normalized * 2
    const r = 239
    const g = Math.round(68 + t * (200 - 68))
    const b = Math.round(68 + t * (30 - 68))
    return `rgb(${r}, ${g}, ${b})`
  } else {
    // Yellow to Green
    const t = (normalized - 0.5) * 2
    const r = Math.round(239 - t * (239 - 34))
    const g = Math.round(200 - t * (200 - 197))
    const b = Math.round(30 + t * (94 - 30))
    return `rgb(${r}, ${g}, ${b})`
  }
}

export function ParameterHeatmap({
  optimizationId,
  parameters,
  objectiveMetric,
}: ParameterHeatmapProps) {
  const [paramX, setParamX] = useState(parameters[0] || '')
  const [paramY, setParamY] = useState(parameters[1] || '')
  const [metric, setMetric] = useState(objectiveMetric)
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (paramX && paramY && paramX !== paramY) {
      fetchHeatmapData()
    }
  }, [paramX, paramY, metric, optimizationId])

  const fetchHeatmapData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await optimizationApi.getHeatmap(optimizationId, paramX, paramY, metric)
      setHeatmapData(data)
    } catch (err: any) {
      console.error('Failed to fetch heatmap data:', err)
      setError(err.response?.data?.detail || 'Failed to load heatmap data')
    } finally {
      setIsLoading(false)
    }
  }

  // Build a map for quick lookup
  const dataMap = useMemo(() => {
    if (!heatmapData) return new Map<string, number>()
    const map = new Map<string, number>()
    for (const point of heatmapData.data) {
      map.set(`${point.x}-${point.y}`, Number(point.value))
    }
    return map
  }, [heatmapData])

  // Calculate min/max for color scaling
  const { minValue, maxValue } = useMemo(() => {
    if (!heatmapData || heatmapData.data.length === 0) {
      return { minValue: 0, maxValue: 0 }
    }
    const values = heatmapData.data.map((d) => Number(d.value))
    return {
      minValue: Math.min(...values),
      maxValue: Math.max(...values),
    }
  }, [heatmapData])

  return (
    <div className="space-y-4">
      {/* Parameter Selectors */}
      <div className="flex flex-wrap gap-4">
        <div className="flex-1 min-w-[150px]">
          <label className="block text-sm font-medium mb-1">X Axis Parameter</label>
          <select
            value={paramX}
            onChange={(e) => setParamX(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            {parameters.map((p) => (
              <option key={p} value={p} disabled={p === paramY}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[150px]">
          <label className="block text-sm font-medium mb-1">Y Axis Parameter</label>
          <select
            value={paramY}
            onChange={(e) => setParamY(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            {parameters.map((p) => (
              <option key={p} value={p} disabled={p === paramX}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[150px]">
          <label className="block text-sm font-medium mb-1">Metric</label>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            {METRICS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Heatmap */}
      {isLoading ? (
        <div className="h-80 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="h-80 flex items-center justify-center text-red-500">
          {error}
        </div>
      ) : heatmapData && heatmapData.x_values.length > 0 && heatmapData.y_values.length > 0 ? (
        <div className="overflow-x-auto">
          <div className="min-w-fit">
            {/* Column headers (X values) */}
            <div className="flex">
              <div className="w-20 shrink-0" /> {/* Empty corner */}
              {heatmapData.x_values.map((x) => (
                <div
                  key={x}
                  className="w-14 h-10 flex items-center justify-center text-xs font-medium shrink-0"
                >
                  {x}
                </div>
              ))}
            </div>

            {/* Rows */}
            {heatmapData.y_values.map((y) => (
              <div key={y} className="flex">
                {/* Row header (Y value) */}
                <div className="w-20 h-14 flex items-center justify-end pr-2 text-xs font-medium shrink-0">
                  {y}
                </div>
                {/* Cells */}
                {heatmapData.x_values.map((x) => {
                  const value = dataMap.get(`${x}-${y}`)
                  const isBest = x === heatmapData.best_x && y === heatmapData.best_y

                  return (
                    <div
                      key={`${x}-${y}`}
                      className={`w-14 h-14 flex items-center justify-center text-xs font-medium shrink-0 relative ${
                        isBest ? 'ring-2 ring-black dark:ring-white ring-inset' : ''
                      }`}
                      style={{
                        backgroundColor:
                          value !== undefined
                            ? interpolateColor(value, minValue, maxValue)
                            : '#e5e7eb',
                        color: value !== undefined && value > (minValue + maxValue) / 2 ? '#000' : '#fff',
                      }}
                      title={`${paramX}=${x}, ${paramY}=${y}: ${value?.toFixed(2) ?? 'N/A'}`}
                    >
                      {value !== undefined ? value.toFixed(1) : '-'}
                      {isBest && (
                        <span className="absolute -top-1 -right-1 text-[8px] bg-black dark:bg-white text-white dark:text-black px-1 rounded">
                          Best
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}

            {/* Axis Labels */}
            <div className="flex justify-center mt-2 text-xs text-gray-500">
              <span className="font-medium">{paramX}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="h-80 flex items-center justify-center text-gray-500">
          Select two different parameters to view heatmap
        </div>
      )}

      {/* Color Legend */}
      {heatmapData && heatmapData.data.length > 0 && (
        <div className="flex items-center gap-2 text-xs">
          <span className="text-gray-500">Low ({minValue.toFixed(2)})</span>
          <div
            className="h-3 flex-1 rounded"
            style={{
              background: 'linear-gradient(to right, rgb(239, 68, 68), rgb(234, 179, 8), rgb(34, 197, 94))',
            }}
          />
          <span className="text-gray-500">High ({maxValue.toFixed(2)})</span>
        </div>
      )}

      {/* Best Parameters Info */}
      {heatmapData && heatmapData.best_value !== null && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <p className="text-sm font-medium text-green-700 dark:text-green-400">
            Best Combination for Selected Parameters
          </p>
          <p className="text-sm text-green-600 dark:text-green-500 mt-1">
            {paramX} = {heatmapData.best_x}, {paramY} = {heatmapData.best_y} →{' '}
            {METRICS.find((m) => m.value === metric)?.label}: {Number(heatmapData.best_value ?? 0).toFixed(2)}
          </p>
        </div>
      )}
    </div>
  )
}
