// Optimization Types

export type OptimizationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export type ObjectiveMetric =
  | 'total_return_percent'
  | 'sharpe_ratio'
  | 'sortino_ratio'
  | 'profit_factor'
  | 'win_rate'
  | 'calmar_ratio'

export interface ParameterRange {
  min: number
  max: number
  step: number
}

export interface OptimizationCreate {
  source_backtest_id: string
  parameter_ranges: Record<string, ParameterRange>
  num_samples: number
  objective_metric: ObjectiveMetric
}

export interface Optimization {
  id: string
  user_id: string
  strategy_id: string
  source_backtest_id?: string
  status: OptimizationStatus
  symbol: string
  exchange: string
  interval: string
  start_date: string
  end_date: string
  initial_capital: number
  num_samples: number
  parameter_ranges: Record<string, ParameterRange>
  objective_metric: string
  progress: number
  completed_samples: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface OptimizationListItem {
  id: string
  strategy_id: string
  source_backtest_id?: string
  status: OptimizationStatus
  symbol: string
  exchange: string
  interval: string
  start_date: string
  end_date: string
  initial_capital: number
  num_samples: number
  objective_metric: string
  progress: number
  completed_samples: number
  created_at: string
  completed_at?: string
  best_return_percent?: number
}

export interface OptimizationProgress {
  id: string
  status: OptimizationStatus
  progress: number
  completed_samples: number
  total_samples: number
  error_message?: string
}

export interface OptimizationResultItem {
  id: string
  parameters: Record<string, number>
  total_return?: number
  total_return_percent?: number
  sharpe_ratio?: number
  sortino_ratio?: number
  max_drawdown?: number
  win_rate?: number
  profit_factor?: number
  calmar_ratio?: number
  total_trades: number
  is_best: boolean
}

export interface OptimizationResults {
  optimization_id: string
  status: OptimizationStatus
  objective_metric: string
  total_samples: number
  best_result?: OptimizationResultItem
  all_results: OptimizationResultItem[]
}

export interface HeatmapDataPoint {
  x: number
  y: number
  value: number
}

export interface HeatmapData {
  param_x: string
  param_y: string
  x_values: number[]
  y_values: number[]
  data: HeatmapDataPoint[]
  best_x?: number
  best_y?: number
  best_value?: number
  metric: string
}

// Strategy configurable parameter (used for optimization form)
export interface ConfigurableParam {
  name: string
  display_name: string
  type: 'int' | 'float' | 'decimal' | 'bool'
  default_value: number | boolean
  min_value?: number
  max_value?: number
  description?: string
}
