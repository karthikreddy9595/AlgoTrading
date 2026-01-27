'use client'

import { Fragment, useState, useEffect } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Check, Loader2, DollarSign, Activity, AlertCircle, Link as LinkIcon } from 'lucide-react'
import { strategyApi, brokerApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'

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
  supported_symbols: string[]
  tags: string[]
  is_featured: boolean
}

interface QuickSubscribeModalProps {
  isOpen: boolean
  onClose: () => void
  strategy: Strategy
  onSuccess?: () => void
}

export function QuickSubscribeModal({
  isOpen,
  onClose,
  strategy,
  onSuccess,
}: QuickSubscribeModalProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [isFetchingBrokers, setIsFetchingBrokers] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Form state
  const [capital, setCapital] = useState<string>(String(strategy.min_capital))
  const [isPaperTrading, setIsPaperTrading] = useState(true)
  const [dryRun, setDryRun] = useState(false)
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [maxPositions, setMaxPositions] = useState<string>('3')
  const [customSymbol, setCustomSymbol] = useState<string>('')
  const [symbolError, setSymbolError] = useState<string>('')
  const [brokerConnections, setBrokerConnections] = useState<any[]>([])
  const [selectedBrokerId, setSelectedBrokerId] = useState<string>('')

  useEffect(() => {
    if (isOpen) {
      // Reset form when modal opens
      setCapital(String(strategy.min_capital))
      setIsPaperTrading(true)
      setDryRun(false)
      setSelectedSymbols([])
      setMaxPositions('3')
      setCustomSymbol('')
      setSymbolError('')
      setError(null)
      setSuccess(false)
      setSelectedBrokerId('')

      // Fetch broker connections
      const fetchBrokerConnections = async () => {
        setIsFetchingBrokers(true)
        try {
          const connections = await brokerApi.getConnections()
          setBrokerConnections(connections)
          // Auto-select if only one active connection
          const activeConnections = connections.filter((c: any) => c.is_active)
          if (activeConnections.length === 1) {
            setSelectedBrokerId(activeConnections[0].id)
          }
        } catch (err) {
          console.error('Failed to fetch broker connections:', err)
        } finally {
          setIsFetchingBrokers(false)
        }
      }

      fetchBrokerConnections()
    }
  }, [isOpen, strategy.min_capital])

  const handleSymbolToggle = (symbol: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol]
    )
  }

  const handleSelectAll = () => {
    const supportedSymbols = strategy.supported_symbols || []
    if (selectedSymbols.length === supportedSymbols.length) {
      setSelectedSymbols([])
    } else {
      setSelectedSymbols([...supportedSymbols])
    }
  }

  const handleAddCustomSymbol = () => {
    setSymbolError('')
    const symbol = customSymbol.trim().toUpperCase()

    // Validate format: EXCHANGE:SYMBOL
    if (!symbol) {
      setSymbolError('Please enter a symbol')
      return
    }

    if (!symbol.includes(':')) {
      setSymbolError('Symbol must include exchange. Example: NSE:RELIANCE or BSE:SENSEX')
      return
    }

    const [exchange, symbolName] = symbol.split(':')
    if (!exchange || !symbolName) {
      setSymbolError('Invalid format. Use EXCHANGE:SYMBOL (e.g., NSE:RELIANCE)')
      return
    }

    // Valid exchanges
    const validExchanges = ['NSE', 'BSE', 'NFO', 'MCX', 'CDS']
    if (!validExchanges.includes(exchange)) {
      setSymbolError(`Invalid exchange. Valid exchanges: ${validExchanges.join(', ')}`)
      return
    }

    if (selectedSymbols.includes(symbol)) {
      setSymbolError('Symbol already added')
      return
    }

    setSelectedSymbols([...selectedSymbols, symbol])
    setCustomSymbol('')
  }

  const handleRemoveSymbol = (symbol: string) => {
    setSelectedSymbols(selectedSymbols.filter((s) => s !== symbol))
  }

  const handleCustomSymbolKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddCustomSymbol()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    const capitalNum = Number(capital)
    if (isNaN(capitalNum) || capitalNum < strategy.min_capital) {
      setError(`Minimum capital is ${formatCurrency(strategy.min_capital)}`)
      return
    }

    if (selectedSymbols.length === 0) {
      setError('Please select at least one trading symbol')
      return
    }

    const maxPos = Number(maxPositions)
    if (isNaN(maxPos) || maxPos < 1) {
      setError('Max positions must be at least 1')
      return
    }

    // Validate broker connection for non-paper trading
    if (!isPaperTrading && !selectedBrokerId) {
      setError('Please select a broker connection for live trading')
      return
    }

    setIsLoading(true)

    try {
      await strategyApi.subscribe({
        strategy_id: strategy.id,
        capital_allocated: capitalNum,
        is_paper_trading: isPaperTrading,
        dry_run: dryRun,
        broker_connection_id: selectedBrokerId || undefined,
        selected_symbols: selectedSymbols,
        max_positions: maxPos,
        config_params: {}, // Use strategy defaults
      })

      setSuccess(true)
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err: any) {
      // Handle different error response formats
      let errorMessage = 'Failed to subscribe to strategy'

      if (err.response?.data) {
        const data = err.response.data

        // Handle FastAPI validation errors (array of error objects)
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail
            .map((e: any) => e.msg || JSON.stringify(e))
            .join(', ')
        }
        // Handle single error object with detail
        else if (typeof data.detail === 'string') {
          errorMessage = data.detail
        }
        // Handle error object with message field
        else if (data.message) {
          errorMessage = data.message
        }
        // Handle validation error object
        else if (data.detail && typeof data.detail === 'object') {
          errorMessage = JSON.stringify(data.detail)
        }
      }

      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                  <div>
                    <Dialog.Title className="text-xl font-bold">
                      Quick Subscribe
                    </Dialog.Title>
                    <p className="text-sm text-gray-500 mt-1">
                      {strategy.name} • {strategy.timeframe}
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                {/* Content */}
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                  {success ? (
                    <div className="text-center py-8">
                      <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Check className="h-8 w-8 text-green-600" />
                      </div>
                      <h3 className="text-lg font-semibold mb-2">Subscription Successful!</h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        You can now start and monitor this strategy from Live Strategies
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Capital Allocation */}
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Capital Allocation
                        </label>
                        <div className="relative">
                          <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                          <input
                            type="number"
                            value={capital}
                            onChange={(e) => setCapital(e.target.value)}
                            min={strategy.min_capital}
                            step="1000"
                            required
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Minimum: {formatCurrency(strategy.min_capital)}
                        </p>
                      </div>

                      {/* Paper Trading Toggle */}
                      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <div>
                          <label className="text-sm font-medium">Paper Trading</label>
                          <p className="text-xs text-gray-500">
                            Practice with virtual money (recommended)
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setIsPaperTrading(!isPaperTrading)}
                          className={cn(
                            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                            isPaperTrading ? 'bg-purple-600' : 'bg-gray-300 dark:bg-gray-600'
                          )}
                        >
                          <span
                            className={cn(
                              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                              isPaperTrading ? 'translate-x-6' : 'translate-x-1'
                            )}
                          />
                        </button>
                      </div>

                      {/* Dry Run Toggle */}
                      <div className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <div>
                          <label className="text-sm font-medium flex items-center gap-2">
                            Dry Run Mode
                            <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded">
                              Testing
                            </span>
                          </label>
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            Log orders without sending them to the broker. Perfect for testing your strategy setup.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setDryRun(!dryRun)}
                          className={cn(
                            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                            dryRun ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                          )}
                        >
                          <span
                            className={cn(
                              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                              dryRun ? 'translate-x-6' : 'translate-x-1'
                            )}
                          />
                        </button>
                      </div>

                      {/* Broker Connection Selection */}
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Broker Connection
                          {!isPaperTrading && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        {isFetchingBrokers ? (
                          <div className="flex items-center gap-2 text-gray-500 text-sm">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading broker connections...
                          </div>
                        ) : brokerConnections.length === 0 ? (
                          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                            <div className="flex items-start gap-2">
                              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                              <div className="text-sm">
                                <p className="text-amber-800 dark:text-amber-200 font-medium">
                                  No broker connection found
                                </p>
                                <p className="text-amber-700 dark:text-amber-300 text-xs mt-1">
                                  You need to connect a broker to view charts and trade live.
                                  {isPaperTrading ? ' Paper trading will work without a broker connection.' : ' Please connect a broker or enable paper trading.'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <select
                              value={selectedBrokerId}
                              onChange={(e) => setSelectedBrokerId(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                            >
                              <option value="">
                                {isPaperTrading ? 'None (Optional)' : 'Select a broker connection'}
                              </option>
                              {brokerConnections.map((broker: any) => (
                                <option key={broker.id} value={broker.id}>
                                  {broker.broker.charAt(0).toUpperCase() + broker.broker.slice(1)}
                                  {broker.is_active ? ' (Active)' : ' (Inactive)'}
                                </option>
                              ))}
                            </select>
                            <p className="text-xs text-gray-500 mt-1">
                              {isPaperTrading
                                ? 'Optional: Select a broker to view live charts even in paper trading'
                                : 'Required for live trading and chart data'}
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Max Positions */}
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Max Positions
                        </label>
                        <div className="relative">
                          <Activity className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                          <input
                            type="number"
                            value={maxPositions}
                            onChange={(e) => setMaxPositions(e.target.value)}
                            min="1"
                            max="10"
                            required
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Maximum number of concurrent positions (1-10)
                        </p>
                      </div>

                      {/* Symbol Selection */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <label className="block text-sm font-medium mb-1">
                              Trading Symbols
                            </label>
                            <p className="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded inline-flex items-center gap-1">
                              <Activity className="h-3 w-3" />
                              You can subscribe to the same strategy multiple times with different symbols
                            </p>
                          </div>
                          {(strategy.supported_symbols || []).length > 0 && (
                            <button
                              type="button"
                              onClick={handleSelectAll}
                              className="text-xs text-purple-600 hover:text-purple-700 font-medium"
                            >
                              {selectedSymbols.length === (strategy.supported_symbols || []).length
                                ? 'Deselect All'
                                : 'Select All'}
                            </button>
                          )}
                        </div>

                        {/* Predefined Symbols (if available) */}
                        {(strategy.supported_symbols || []).length > 0 && (
                          <div>
                            <p className="text-xs text-gray-500 mb-2">Select from strategy symbols:</p>
                            <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto p-2 border border-gray-200 dark:border-gray-700 rounded-lg">
                              {(strategy.supported_symbols || []).map((symbol) => (
                                <label
                                  key={symbol}
                                  className={cn(
                                    'flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors',
                                    selectedSymbols.includes(symbol)
                                      ? 'bg-purple-100 dark:bg-purple-900/30 border border-purple-300 dark:border-purple-700'
                                      : 'bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-transparent'
                                  )}
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedSymbols.includes(symbol)}
                                    onChange={() => handleSymbolToggle(symbol)}
                                    className="rounded border-gray-300 text-purple-600 focus:ring-purple-600"
                                  />
                                  <span className="text-sm font-medium">{symbol}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Add Custom Symbol */}
                        <div>
                          <p className="text-xs text-gray-500 mb-2">
                            Or add custom symbols:
                          </p>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={customSymbol}
                              onChange={(e) => setCustomSymbol(e.target.value)}
                              onKeyPress={handleCustomSymbolKeyPress}
                              placeholder="NSE:RELIANCE"
                              className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                            />
                            <button
                              type="button"
                              onClick={handleAddCustomSymbol}
                              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
                            >
                              Add
                            </button>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Format: <span className="font-mono font-semibold">EXCHANGE:SYMBOL</span>
                            <br />
                            Examples: <span className="font-mono">NSE:RELIANCE</span>, <span className="font-mono">NSE:TCS</span>, <span className="font-mono">BSE:SENSEX</span>
                            <br />
                            Valid exchanges: NSE, BSE, NFO, MCX, CDS
                          </p>
                          {symbolError && (
                            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                              {symbolError}
                            </p>
                          )}
                        </div>

                        {/* Selected Symbols Display */}
                        {selectedSymbols.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-500 mb-2">
                              Selected symbols ({selectedSymbols.length}):
                            </p>
                            <div className="flex flex-wrap gap-2 p-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50 max-h-32 overflow-y-auto">
                              {selectedSymbols.map((symbol) => (
                                <div
                                  key={symbol}
                                  className="flex items-center gap-1 px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-md text-sm"
                                >
                                  <span className="font-mono font-medium">{symbol}</span>
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveSymbol(symbol)}
                                    className="ml-1 hover:text-purple-900 dark:hover:text-purple-100"
                                    title="Remove symbol"
                                  >
                                    <X className="h-3 w-3" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedSymbols.length === 0 && (
                          <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-2 rounded border border-amber-200 dark:border-amber-800">
                            Please select or add at least one symbol to continue
                          </p>
                        )}
                      </div>

                      {/* Error Message */}
                      {error && (
                        <div className="flex items-start gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                        </div>
                      )}

                      {/* Submit Button */}
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={onClose}
                          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isLoading}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50"
                        >
                          {isLoading ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Subscribing...
                            </>
                          ) : (
                            <>
                              <Check className="h-4 w-4" />
                              Subscribe Now
                            </>
                          )}
                        </button>
                      </div>
                    </>
                  )}
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
