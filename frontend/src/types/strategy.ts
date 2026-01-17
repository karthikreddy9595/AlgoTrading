// Strategy Types for AlgoTrading Platform

export interface Strategy {
  id: string
  name: string
  slug: string
  description: string | null
  version: string
  min_capital: number
  expected_return_percent: number | null
  max_drawdown_percent: number | null
  timeframe: string | null
  tags: string[] | null
  is_featured: boolean
}

export interface ConfigurableParam {
  name: string
  display_name: string
  type: 'int' | 'float' | 'decimal' | 'bool'
  default_value: number | boolean
  min_value: number | null
  max_value: number | null
  description: string | null
}

export interface StrategyDetail extends Strategy {
  author: string
  long_description: string | null
  supported_symbols: string[] | null
  is_active: boolean
  module_path: string
  class_name: string
  created_at: string
  updated_at: string
  configurable_params: ConfigurableParam[]
}

export interface StrategySubscription {
  id: string
  user_id: string
  strategy_id: string
  broker_connection_id: string | null
  status: 'inactive' | 'active' | 'paused' | 'stopped'
  capital_allocated: number
  is_paper_trading: boolean
  // Risk management
  max_drawdown_percent: number
  daily_loss_limit: number | null
  per_trade_stop_loss_percent: number
  max_positions: number
  // Strategy configuration
  config_params: Record<string, number | boolean> | null
  selected_symbols: string[] | null
  // Scheduling
  scheduled_start: string | null
  scheduled_stop: string | null
  active_days: number[]
  // State
  current_pnl: number
  today_pnl: number
  last_started_at: string | null
  last_stopped_at: string | null
  created_at: string
  // Nested
  strategy?: Strategy
}

export interface SubscriptionCreateData {
  strategy_id: string
  broker_connection_id?: string
  capital_allocated: number
  is_paper_trading: boolean
  max_drawdown_percent: number
  daily_loss_limit?: number
  per_trade_stop_loss_percent: number
  max_positions: number
  config_params?: Record<string, number | boolean>
  selected_symbols: string[]
  scheduled_start?: string
  scheduled_stop?: string
  active_days?: number[]
}

export interface SymbolInfo {
  symbol: string
  exchange: string
  name: string
  segment?: string
}

export type StrategyAction = 'start' | 'stop' | 'pause' | 'resume'
