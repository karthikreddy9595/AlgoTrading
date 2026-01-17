'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Clock,
  DollarSign,
  TrendingDown,
  CheckCircle2,
  AlertCircle,
  Play,
  Pause,
  Square,
  Settings,
  Loader2,
  Search,
  X,
  Star
} from 'lucide-react'
import { strategyApi, marketApi, userApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import type { StrategyDetail, StrategySubscription, ConfigurableParam, SymbolInfo } from '@/types/strategy'

export default function StrategyDetailPage() {
  const { slug } = useParams()
  const router = useRouter()

  const [strategy, setStrategy] = useState<StrategyDetail | null>(null)
  const [subscription, setSubscription] = useState<StrategySubscription | null>(null)
  const [brokerConnections, setBrokerConnections] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Subscription form state
  const [formData, setFormData] = useState({
    capital_allocated: 0,
    is_paper_trading: true,
    max_drawdown_percent: 10,
    daily_loss_limit: 0,
    per_trade_stop_loss_percent: 2,
    max_positions: 5,
    config_params: {} as Record<string, number | boolean>,
    selected_symbols: [] as string[],
    broker_connection_id: '' as string | undefined,
  })

  // Symbol search state
  const [symbolSearch, setSymbolSearch] = useState('')
  const [searchResults, setSearchResults] = useState<SymbolInfo[]>([])
  const [popularSymbols, setPopularSymbols] = useState<SymbolInfo[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch strategy by slug first
        const strategyBasic = await strategyApi.getBySlug(slug as string)

        // Fetch strategy with configurable params
        const strategyDetail = await strategyApi.getWithConfig(strategyBasic.id)
        setStrategy(strategyDetail)

        // Set default values for config params
        const defaultConfig: Record<string, number | boolean> = {}
        strategyDetail.configurable_params?.forEach((p: ConfigurableParam) => {
          defaultConfig[p.name] = p.default_value
        })

        setFormData(prev => ({
          ...prev,
          capital_allocated: strategyDetail.min_capital || 10000,
          config_params: defaultConfig,
        }))

        // Check for existing subscription
        const subs = await strategyApi.getMySubscriptions()
        const existing = subs.find((s: StrategySubscription) => s.strategy_id === strategyDetail.id)
        if (existing) {
          setSubscription(existing)
        }

        // Fetch broker connections
        const connections = await userApi.getBrokerConnections()
        setBrokerConnections(connections)

        // Fetch popular symbols
        const popular = await marketApi.getPopularSymbols()
        setPopularSymbols(popular.symbols || [])

      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load strategy')
      } finally {
        setIsLoading(false)
      }
    }

    if (slug) {
      fetchData()
    }
  }, [slug])

  // Debounced symbol search
  useEffect(() => {
    const searchSymbols = async () => {
      if (symbolSearch.length < 2) {
        setSearchResults([])
        return
      }

      setIsSearching(true)
      try {
        const results = await marketApi.searchSymbols(symbolSearch)
        setSearchResults(results.symbols || [])
      } catch (err) {
        console.error('Symbol search failed:', err)
      } finally {
        setIsSearching(false)
      }
    }

    const debounce = setTimeout(searchSymbols, 300)
    return () => clearTimeout(debounce)
  }, [symbolSearch])

  const handleAddSymbol = (symbol: SymbolInfo) => {
    const symbolKey = `${symbol.exchange}:${symbol.symbol}`
    if (!formData.selected_symbols.includes(symbolKey)) {
      setFormData(prev => ({
        ...prev,
        selected_symbols: [...prev.selected_symbols, symbolKey],
      }))
    }
    setSymbolSearch('')
    setSearchResults([])
  }

  const handleRemoveSymbol = (symbolKey: string) => {
    setFormData(prev => ({
      ...prev,
      selected_symbols: prev.selected_symbols.filter(s => s !== symbolKey),
    }))
  }

  const handleConfigChange = (name: string, value: number | boolean) => {
    setFormData(prev => ({
      ...prev,
      config_params: {
        ...prev.config_params,
        [name]: value,
      },
    }))
  }

  const handleSubscribe = async () => {
    if (!strategy) return

    if (formData.selected_symbols.length === 0) {
      setSubmitError('Please select at least one symbol to trade')
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const subscriptionData = {
        strategy_id: strategy.id,
        capital_allocated: formData.capital_allocated,
        is_paper_trading: formData.is_paper_trading,
        max_drawdown_percent: formData.max_drawdown_percent,
        daily_loss_limit: formData.daily_loss_limit || undefined,
        per_trade_stop_loss_percent: formData.per_trade_stop_loss_percent,
        max_positions: formData.max_positions,
        config_params: formData.config_params,
        selected_symbols: formData.selected_symbols,
        broker_connection_id: formData.broker_connection_id || undefined,
      }

      const newSubscription = await strategyApi.subscribe(subscriptionData)
      setSubscription(newSubscription)
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || 'Failed to subscribe')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleAction = async (action: 'start' | 'stop' | 'pause' | 'resume') => {
    if (!subscription) return

    try {
      const updated = await strategyApi.subscriptionAction(subscription.id, action)
      setSubscription(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || `Failed to ${action} strategy`)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">{error || 'Strategy not found'}</p>
        <Link href="/dashboard/strategies" className="text-blue-600 hover:underline mt-4 inline-block">
          Back to Strategies
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/dashboard/strategies"
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{strategy.name}</h1>
            {strategy.is_featured && (
              <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
            )}
            <span className="text-sm text-gray-500">v{strategy.version}</span>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mt-1">{strategy.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Strategy Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <DollarSign className="h-4 w-4" />
                <span className="text-sm">Min Capital</span>
              </div>
              <p className="text-xl font-semibold">{formatCurrency(strategy.min_capital)}</p>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <TrendingDown className="h-4 w-4" />
                <span className="text-sm">Max Drawdown</span>
              </div>
              <p className="text-xl font-semibold text-red-600">
                {strategy.max_drawdown_percent ? `${strategy.max_drawdown_percent}%` : 'N/A'}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
              <div className="flex items-center gap-2 text-gray-500 mb-1">
                <Clock className="h-4 w-4" />
                <span className="text-sm">Timeframe</span>
              </div>
              <p className="text-xl font-semibold">{strategy.timeframe || 'N/A'}</p>
            </div>
          </div>

          {/* Long Description */}
          {strategy.long_description && (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <h2 className="text-lg font-semibold mb-4">About this Strategy</h2>
              <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {strategy.long_description}
              </p>
            </div>
          )}

          {/* Supported Symbols */}
          {strategy.supported_symbols && strategy.supported_symbols.length > 0 && (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <h2 className="text-lg font-semibold mb-4">Tested on Symbols</h2>
              <div className="flex flex-wrap gap-2">
                {strategy.supported_symbols.map(symbol => (
                  <span
                    key={symbol}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full text-sm"
                  >
                    {symbol}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tags */}
          {strategy.tags && strategy.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {strategy.tags.map(tag => (
                <span
                  key={tag}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded-full text-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Subscription Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 sticky top-6">
            {subscription ? (
              // Existing Subscription
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Your Subscription</h2>
                  <span className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    subscription.status === 'active' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
                    subscription.status === 'paused' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
                    subscription.status === 'stopped' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
                    subscription.status === 'inactive' && 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
                  )}>
                    {subscription.status}
                  </span>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Capital</span>
                    <span className="font-medium">{formatCurrency(subscription.capital_allocated)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Today's P&L</span>
                    <span className={cn(
                      'font-medium',
                      subscription.today_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {formatCurrency(subscription.today_pnl)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Total P&L</span>
                    <span className={cn(
                      'font-medium',
                      subscription.current_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {formatCurrency(subscription.current_pnl)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Mode</span>
                    <span className={cn(
                      'font-medium',
                      subscription.is_paper_trading ? 'text-yellow-600' : 'text-green-600'
                    )}>
                      {subscription.is_paper_trading ? 'Paper Trading' : 'Live Trading'}
                    </span>
                  </div>
                  {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
                    <div className="text-sm">
                      <span className="text-gray-500">Symbols</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {subscription.selected_symbols.map(s => (
                          <span key={s} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  {subscription.status === 'inactive' || subscription.status === 'stopped' ? (
                    <button
                      onClick={() => handleAction('start')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                    >
                      <Play className="h-4 w-4" />
                      Start
                    </button>
                  ) : subscription.status === 'active' ? (
                    <>
                      <button
                        onClick={() => handleAction('pause')}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg"
                      >
                        <Pause className="h-4 w-4" />
                        Pause
                      </button>
                      <button
                        onClick={() => handleAction('stop')}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
                      >
                        <Square className="h-4 w-4" />
                        Stop
                      </button>
                    </>
                  ) : subscription.status === 'paused' ? (
                    <>
                      <button
                        onClick={() => handleAction('resume')}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                      >
                        <Play className="h-4 w-4" />
                        Resume
                      </button>
                      <button
                        onClick={() => handleAction('stop')}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
                      >
                        <Square className="h-4 w-4" />
                        Stop
                      </button>
                    </>
                  ) : null}
                </div>

                <Link
                  href={`/dashboard/strategies/${slug}/monitor`}
                  className="block mt-4 text-center text-blue-600 hover:underline text-sm"
                >
                  View Detailed Monitor
                </Link>
              </div>
            ) : (
              // Subscription Form
              <div>
                <h2 className="text-lg font-semibold mb-4">Subscribe to Strategy</h2>

                {submitError && (
                  <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded-lg text-sm">
                    {submitError}
                  </div>
                )}

                <div className="space-y-4">
                  {/* Capital */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Capital to Allocate</label>
                    <input
                      type="number"
                      min={strategy.min_capital}
                      value={formData.capital_allocated}
                      onChange={e => setFormData(prev => ({ ...prev, capital_allocated: Number(e.target.value) }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                    />
                    <p className="text-xs text-gray-500 mt-1">Minimum: {formatCurrency(strategy.min_capital)}</p>
                  </div>

                  {/* Symbol Selection */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Select Symbols to Trade</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search symbols..."
                        value={symbolSearch}
                        onChange={e => setSymbolSearch(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                      />
                    </div>

                    {/* Search Results */}
                    {searchResults.length > 0 && (
                      <div className="mt-2 border border-gray-200 dark:border-gray-700 rounded-lg max-h-40 overflow-y-auto">
                        {searchResults.map(sym => (
                          <button
                            key={`${sym.exchange}:${sym.symbol}`}
                            onClick={() => handleAddSymbol(sym)}
                            className="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-sm flex justify-between"
                          >
                            <span className="font-medium">{sym.symbol}</span>
                            <span className="text-gray-500">{sym.exchange}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Popular Symbols */}
                    {symbolSearch.length === 0 && popularSymbols.length > 0 && formData.selected_symbols.length === 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-gray-500 mb-1">Popular:</p>
                        <div className="flex flex-wrap gap-1">
                          {popularSymbols.slice(0, 8).map(sym => (
                            <button
                              key={`${sym.exchange}:${sym.symbol}`}
                              onClick={() => handleAddSymbol(sym)}
                              className="px-2 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-xs"
                            >
                              {sym.symbol}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Selected Symbols */}
                    {formData.selected_symbols.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {formData.selected_symbols.map(s => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded text-xs"
                          >
                            {s}
                            <button onClick={() => handleRemoveSymbol(s)}>
                              <X className="h-3 w-3" />
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Strategy Parameters */}
                  {strategy.configurable_params && strategy.configurable_params.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium mb-2">Strategy Parameters</label>
                      <div className="space-y-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        {strategy.configurable_params.map(param => (
                          <div key={param.name}>
                            <div className="flex justify-between text-sm mb-1">
                              <span>{param.display_name}</span>
                              <span className="text-gray-500">{formData.config_params[param.name]}</span>
                            </div>
                            {param.type === 'bool' ? (
                              <input
                                type="checkbox"
                                checked={formData.config_params[param.name] as boolean}
                                onChange={e => handleConfigChange(param.name, e.target.checked)}
                              />
                            ) : (
                              <input
                                type="range"
                                min={param.min_value || 0}
                                max={param.max_value || 100}
                                value={formData.config_params[param.name] as number}
                                onChange={e => handleConfigChange(param.name, Number(e.target.value))}
                                className="w-full"
                              />
                            )}
                            {param.description && (
                              <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Risk Management */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Risk Management</label>
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs text-gray-500">Max Drawdown %</label>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={formData.max_drawdown_percent}
                          onChange={e => setFormData(prev => ({ ...prev, max_drawdown_percent: Number(e.target.value) }))}
                          className="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500">Max Positions</label>
                        <input
                          type="number"
                          min={1}
                          max={20}
                          value={formData.max_positions}
                          onChange={e => setFormData(prev => ({ ...prev, max_positions: Number(e.target.value) }))}
                          className="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500">Per Trade Stop Loss %</label>
                        <input
                          type="number"
                          min={0.5}
                          max={10}
                          step={0.5}
                          value={formData.per_trade_stop_loss_percent}
                          onChange={e => setFormData(prev => ({ ...prev, per_trade_stop_loss_percent: Number(e.target.value) }))}
                          className="w-full px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Paper Trading Toggle */}
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="paper_trading"
                      checked={formData.is_paper_trading}
                      onChange={e => setFormData(prev => ({ ...prev, is_paper_trading: e.target.checked }))}
                      className="h-4 w-4"
                    />
                    <label htmlFor="paper_trading" className="text-sm">
                      Paper Trading Mode
                      <span className="text-gray-500 ml-1">(Recommended for testing)</span>
                    </label>
                  </div>

                  {/* Broker Connection (for live trading) */}
                  {!formData.is_paper_trading && brokerConnections.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Broker Connection</label>
                      <select
                        value={formData.broker_connection_id || ''}
                        onChange={e => setFormData(prev => ({ ...prev, broker_connection_id: e.target.value || undefined }))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                      >
                        <option value="">Select broker...</option>
                        {brokerConnections.map(conn => (
                          <option key={conn.id} value={conn.id}>
                            {conn.broker} - {conn.client_id}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Submit */}
                  <button
                    onClick={handleSubscribe}
                    disabled={isSubmitting || formData.selected_symbols.length === 0}
                    className={cn(
                      'w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2',
                      isSubmitting || formData.selected_symbols.length === 0
                        ? 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    )}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Subscribing...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4" />
                        Subscribe
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
