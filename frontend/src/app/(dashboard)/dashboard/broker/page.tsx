'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import {
  Link2,
  Check,
  X,
  Loader2,
  Clock,
  TrendingUp,
  BarChart3,
  Zap,
} from 'lucide-react'
import { brokerApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface BrokerInfo {
  name: string
  display_name: string
  description: string
  auth_type: 'oauth' | 'api_key' | 'totp'
  logo_url: string | null
}

interface BrokerDetails {
  name: string
  display_name: string
  version: string
  description: string
  auth_type: string
  requires_api_key: boolean
  requires_api_secret: boolean
  requires_totp: boolean
  token_expiry_hours: number
  exchanges: string[]
  capabilities: {
    trading: boolean
    market_data: boolean
    historical_data: boolean
    streaming: boolean
    options: boolean
    futures: boolean
    equity: boolean
    commodities: boolean
    currency: boolean
  }
  logo_url: string | null
}

interface ConnectionStatus {
  broker: string
  connected: boolean
  expires_at: string | null
  needs_refresh: boolean
}

export default function BrokerPage() {
  const searchParams = useSearchParams()
  const [brokers, setBrokers] = useState<BrokerInfo[]>([])
  const [connections, setConnections] = useState<Record<string, ConnectionStatus>>({})
  const [selectedBroker, setSelectedBroker] = useState<BrokerDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [connectingBroker, setConnectingBroker] = useState<string | null>(null)

  // API Key form state
  const [showApiKeyForm, setShowApiKeyForm] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [totp, setTotp] = useState('')

  useEffect(() => {
    fetchBrokers()

    // Handle OAuth callback
    const brokerParam = searchParams.get('broker')
    const statusParam = searchParams.get('status')

    if (brokerParam && statusParam) {
      if (statusParam === 'success') {
        toast.success(`Connected to ${brokerParam} successfully`)
      } else if (statusParam === 'error') {
        const message = searchParams.get('message') || 'Connection failed'
        toast.error(message)
      }
      // Clear URL params
      window.history.replaceState({}, '', '/dashboard/broker')
    }
  }, [searchParams])

  const fetchBrokers = async () => {
    try {
      const data = await brokerApi.listAvailable()
      setBrokers(data)

      // Fetch connection status for each broker
      const statuses: Record<string, ConnectionStatus> = {}
      for (const broker of data) {
        try {
          const status = await brokerApi.getStatus(broker.name)
          statuses[broker.name] = status
        } catch {
          statuses[broker.name] = {
            broker: broker.name,
            connected: false,
            expires_at: null,
            needs_refresh: false,
          }
        }
      }
      setConnections(statuses)
    } catch (error) {
      console.error('Failed to fetch brokers:', error)
      toast.error('Failed to load brokers')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectBroker = async (brokerName: string) => {
    try {
      const details = await brokerApi.getInfo(brokerName)
      setSelectedBroker(details)
      setShowApiKeyForm(false)
      setApiKey('')
      setApiSecret('')
      setTotp('')
    } catch {
      toast.error('Failed to load broker details')
    }
  }

  const handleConnect = async () => {
    if (!selectedBroker) return

    setConnectingBroker(selectedBroker.name)

    try {
      if (selectedBroker.auth_type === 'oauth') {
        // OAuth flow - redirect to broker
        const { auth_url } = await brokerApi.getLoginUrl(selectedBroker.name)
        window.location.href = auth_url
      } else {
        // API key flow
        setShowApiKeyForm(true)
        setConnectingBroker(null)
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to initiate connection')
      setConnectingBroker(null)
    }
  }

  const handleApiKeySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedBroker) return

    setConnectingBroker(selectedBroker.name)

    try {
      await brokerApi.connect(selectedBroker.name, {
        api_key: apiKey,
        api_secret: apiSecret,
        totp: totp || undefined,
      })

      toast.success(`Connected to ${selectedBroker.display_name}`)
      setShowApiKeyForm(false)
      setSelectedBroker(null)
      fetchBrokers()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to connect')
    } finally {
      setConnectingBroker(null)
    }
  }

  const handleDisconnect = async (brokerName: string) => {
    try {
      await brokerApi.disconnect(brokerName)
      toast.success('Broker disconnected')
      fetchBrokers()
      if (selectedBroker?.name === brokerName) {
        setSelectedBroker(null)
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to disconnect')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Connect Broker</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Connect your trading account to start automated trading
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Broker List */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Available Brokers</h2>

            {brokers.length === 0 ? (
              <div className="text-center py-12">
                <Link2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">No brokers available</h3>
                <p className="text-sm text-gray-500">
                  No broker plugins are currently configured on this server.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {brokers.map((broker) => {
                  const status = connections[broker.name]
                  const isConnected = status?.connected

                  return (
                    <div
                      key={broker.name}
                      onClick={() => handleSelectBroker(broker.name)}
                      className={cn(
                        'p-4 rounded-lg border cursor-pointer transition-all',
                        selectedBroker?.name === broker.name
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center text-blue-600 font-bold text-lg">
                            {broker.display_name.charAt(0)}
                          </div>
                          <div>
                            <h3 className="font-medium text-gray-900 dark:text-white">{broker.display_name}</h3>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {broker.auth_type === 'oauth' ? 'OAuth Login' : 'API Key'}
                            </p>
                          </div>
                        </div>
                        {isConnected && (
                          <span className="flex items-center gap-1 px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded">
                            <Check className="h-3 w-3" />
                            Connected
                          </span>
                        )}
                      </div>
                      <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {broker.description}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Broker Details / Connection Form */}
        <div>
          {selectedBroker ? (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 sticky top-20">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-14 h-14 rounded-lg bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center text-blue-600 font-bold text-xl">
                  {selectedBroker.display_name.charAt(0)}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedBroker.display_name}</h2>
                  <p className="text-sm text-gray-500">v{selectedBroker.version}</p>
                </div>
              </div>

              {/* Capabilities */}
              <div className="mb-4">
                <h3 className="text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Capabilities</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedBroker.capabilities.equity && (
                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 rounded">
                      Equity
                    </span>
                  )}
                  {selectedBroker.capabilities.options && (
                    <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 rounded">
                      Options
                    </span>
                  )}
                  {selectedBroker.capabilities.futures && (
                    <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400 rounded">
                      Futures
                    </span>
                  )}
                  {selectedBroker.capabilities.streaming && (
                    <span className="px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      Real-time
                    </span>
                  )}
                  {selectedBroker.capabilities.historical_data && (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 rounded flex items-center gap-1">
                      <BarChart3 className="h-3 w-3" />
                      Historical
                    </span>
                  )}
                </div>
              </div>

              {/* Exchanges */}
              <div className="mb-4">
                <h3 className="text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Exchanges</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedBroker.exchanges.join(', ')}
                </p>
              </div>

              {/* Token Expiry Info */}
              <div className="mb-6 flex items-center gap-2 text-sm text-gray-500">
                <Clock className="h-4 w-4" />
                <span>Token valid for {selectedBroker.token_expiry_hours} hours</span>
              </div>

              {/* API Key Form */}
              {showApiKeyForm ? (
                <form onSubmit={handleApiKeySubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">API Key</label>
                    <input
                      type="text"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter your API key"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">API Secret</label>
                    <input
                      type="password"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter your API secret"
                      required
                    />
                  </div>
                  {selectedBroker.requires_totp && (
                    <div>
                      <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">TOTP Code</label>
                      <input
                        type="text"
                        value={totp}
                        onChange={(e) => setTotp(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="6-digit code"
                        maxLength={6}
                        required
                      />
                    </div>
                  )}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowApiKeyForm(false)}
                      className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={connectingBroker === selectedBroker.name}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {connectingBroker === selectedBroker.name ? (
                        <Loader2 className="h-4 w-4 animate-spin mx-auto" />
                      ) : (
                        'Connect'
                      )}
                    </button>
                  </div>
                </form>
              ) : connections[selectedBroker.name]?.connected ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <Check className="h-5 w-5 text-green-600" />
                    <span className="text-green-800 dark:text-green-400 font-medium">
                      Connected
                    </span>
                  </div>
                  {connections[selectedBroker.name]?.expires_at && (
                    <p className="text-xs text-gray-500 text-center">
                      Expires: {new Date(connections[selectedBroker.name].expires_at!).toLocaleString()}
                    </p>
                  )}
                  <button
                    onClick={() => handleDisconnect(selectedBroker.name)}
                    className="w-full px-4 py-2 border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    Disconnect
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleConnect}
                  disabled={connectingBroker === selectedBroker.name}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connectingBroker === selectedBroker.name ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Link2 className="h-4 w-4" />
                      Connect {selectedBroker.display_name}
                    </>
                  )}
                </button>
              )}
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <div className="text-center py-8">
                <Link2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="font-medium mb-2 text-gray-900 dark:text-white">Select a Broker</h3>
                <p className="text-sm text-gray-500">
                  Click on a broker to view details and connect
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
