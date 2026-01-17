'use client'

import { useState, useEffect } from 'react'
import { X, Settings2, Loader2, AlertCircle } from 'lucide-react'
import { strategyApi, optimizationApi } from '@/lib/api'
import { ConfigurableParam, ParameterRange, ObjectiveMetric } from '@/types/optimization'
import { toast } from 'sonner'

interface OptimizationModalProps {
  backtestId: string
  strategyId: string
  onClose: () => void
  onStarted: (optimizationId: string) => void
}

interface ParamConfig {
  min: number
  max: number
  step: number
  enabled: boolean
}

const OBJECTIVE_METRICS: { value: ObjectiveMetric; label: string }[] = [
  { value: 'total_return_percent', label: 'Total Return %' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'sortino_ratio', label: 'Sortino Ratio' },
  { value: 'profit_factor', label: 'Profit Factor' },
  { value: 'win_rate', label: 'Win Rate' },
  { value: 'calmar_ratio', label: 'Calmar Ratio' },
]

export function OptimizationModal({
  backtestId,
  strategyId,
  onClose,
  onStarted,
}: OptimizationModalProps) {
  const [params, setParams] = useState<ConfigurableParam[]>([])
  const [paramConfigs, setParamConfigs] = useState<Record<string, ParamConfig>>({})
  const [numSamples, setNumSamples] = useState(100)
  const [objectiveMetric, setObjectiveMetric] = useState<ObjectiveMetric>('total_return_percent')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStrategyConfig()
  }, [strategyId])

  const fetchStrategyConfig = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const strategyData = await strategyApi.getWithConfig(strategyId)
      const configurableParams = strategyData.configurable_params || []
      setParams(configurableParams)

      // Initialize param configs with defaults
      const configs: Record<string, ParamConfig> = {}
      for (const param of configurableParams) {
        if (param.type !== 'bool') {
          configs[param.name] = {
            min: param.min_value ?? param.default_value * 0.5,
            max: param.max_value ?? param.default_value * 1.5,
            step: param.type === 'int' ? 1 : 0.1,
            enabled: true,
          }
        }
      }
      setParamConfigs(configs)
    } catch (err: any) {
      console.error('Failed to fetch strategy config:', err)
      setError(err.response?.data?.detail || 'Failed to load strategy parameters')
    } finally {
      setIsLoading(false)
    }
  }

  const updateParamConfig = (name: string, field: keyof ParamConfig, value: number | boolean) => {
    setParamConfigs((prev) => ({
      ...prev,
      [name]: { ...prev[name], [field]: value },
    }))
  }

  const handleSubmit = async () => {
    // Validate at least 2 parameters are enabled
    const enabledParams = Object.entries(paramConfigs).filter(([_, config]) => config.enabled)
    if (enabledParams.length < 2) {
      toast.error('Please enable at least 2 parameters for optimization')
      return
    }

    // Validate ranges
    for (const [name, config] of enabledParams) {
      if (config.min >= config.max) {
        toast.error(`${name}: Min must be less than Max`)
        return
      }
      if (config.step <= 0) {
        toast.error(`${name}: Step must be positive`)
        return
      }
    }

    setIsSubmitting(true)
    try {
      const parameterRanges: Record<string, ParameterRange> = {}
      for (const [name, config] of enabledParams) {
        parameterRanges[name] = {
          min: config.min,
          max: config.max,
          step: config.step,
        }
      }

      const response = await optimizationApi.run({
        source_backtest_id: backtestId,
        parameter_ranges: parameterRanges,
        num_samples: numSamples,
        objective_metric: objectiveMetric,
      })

      toast.success('Optimization started')
      onStarted(response.id)
    } catch (err: any) {
      console.error('Failed to start optimization:', err)
      toast.error(err.response?.data?.detail || 'Failed to start optimization')
    } finally {
      setIsSubmitting(false)
    }
  }

  const numericParams = params.filter((p) => p.type !== 'bool')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Parameter Optimization</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-8rem)]">
          {isLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <AlertCircle className="h-10 w-10 text-red-500 mb-3" />
              <p className="text-gray-500">{error}</p>
              <button
                onClick={fetchStrategyConfig}
                className="mt-3 px-4 py-2 text-sm bg-primary text-white rounded-lg"
              >
                Try Again
              </button>
            </div>
          ) : numericParams.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              This strategy has no configurable numeric parameters.
            </div>
          ) : (
            <div className="space-y-6">
              {/* Parameter Ranges */}
              <div>
                <h3 className="text-sm font-medium mb-3">Parameter Ranges</h3>
                <p className="text-xs text-gray-500 mb-4">
                  Select parameters to optimize and define their search ranges.
                </p>
                <div className="space-y-4">
                  {numericParams.map((param) => {
                    const config = paramConfigs[param.name]
                    if (!config) return null

                    return (
                      <div
                        key={param.name}
                        className={`p-3 rounded-lg border ${
                          config.enabled
                            ? 'border-primary/50 bg-primary/5'
                            : 'border-gray-200 dark:border-gray-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={config.enabled}
                              onChange={(e) =>
                                updateParamConfig(param.name, 'enabled', e.target.checked)
                              }
                              className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                            />
                            <span className="font-medium text-sm">{param.display_name}</span>
                          </label>
                          <span className="text-xs text-gray-500">
                            Default: {param.default_value}
                          </span>
                        </div>
                        {param.description && (
                          <p className="text-xs text-gray-500 mb-2">{param.description}</p>
                        )}
                        {config.enabled && (
                          <div className="grid grid-cols-3 gap-3 mt-2">
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Min</label>
                              <input
                                type="number"
                                value={config.min}
                                onChange={(e) =>
                                  updateParamConfig(param.name, 'min', parseFloat(e.target.value))
                                }
                                step={param.type === 'int' ? 1 : 0.01}
                                className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Max</label>
                              <input
                                type="number"
                                value={config.max}
                                onChange={(e) =>
                                  updateParamConfig(param.name, 'max', parseFloat(e.target.value))
                                }
                                step={param.type === 'int' ? 1 : 0.01}
                                className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Step</label>
                              <input
                                type="number"
                                value={config.step}
                                onChange={(e) =>
                                  updateParamConfig(param.name, 'step', parseFloat(e.target.value))
                                }
                                step={param.type === 'int' ? 1 : 0.01}
                                min={0.01}
                                className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Optimization Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Number of Samples</label>
                  <p className="text-xs text-gray-500 mb-2">
                    Random parameter combinations to test (50-200)
                  </p>
                  <input
                    type="range"
                    min={50}
                    max={200}
                    value={numSamples}
                    onChange={(e) => setNumSamples(parseInt(e.target.value))}
                    className="w-full"
                  />
                  <div className="text-center text-sm font-medium">{numSamples}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Optimize For</label>
                  <p className="text-xs text-gray-500 mb-2">Metric to maximize</p>
                  <select
                    value={objectiveMetric}
                    onChange={(e) => setObjectiveMetric(e.target.value as ObjectiveMetric)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
                  >
                    {OBJECTIVE_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || isSubmitting || numericParams.length < 2}
            className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Start Optimization
          </button>
        </div>
      </div>
    </div>
  )
}
