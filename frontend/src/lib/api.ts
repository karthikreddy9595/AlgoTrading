import axios, { AxiosError, AxiosInstance } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  register: async (data: { email: string; password: string; full_name: string }) => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  login: async (data: { email: string; password: string }) => {
    const response = await api.post('/auth/login', data)
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    return response.data
  },

  googleLogin: () => {
    window.location.href = `${API_URL}/api/v1/auth/google/login`
  },
}

// User API
export const userApi = {
  getProfile: async () => {
    const response = await api.get('/users/me')
    return response.data
  },

  updateProfile: async (data: { full_name?: string; phone?: string }) => {
    const response = await api.patch('/users/me', data)
    return response.data
  },

  getBrokerConnections: async () => {
    const response = await api.get('/users/me/broker-connections')
    return response.data
  },

  deleteBrokerConnection: async (connectionId: string) => {
    const response = await api.delete(`/users/me/broker-connections/${connectionId}`)
    return response.data
  },

  changePassword: async (data: { current_password: string; new_password: string }) => {
    const response = await api.post('/users/me/change-password', data)
    return response.data
  },
}

// Strategy API
export const strategyApi = {
  list: async (params?: { skip?: number; limit?: number; is_featured?: boolean; tag?: string }) => {
    const response = await api.get('/strategies', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get(`/strategies/${id}`)
    return response.data
  },

  getBySlug: async (slug: string) => {
    const response = await api.get(`/strategies/slug/${slug}`)
    return response.data
  },

  getWithConfig: async (id: string) => {
    const response = await api.get(`/strategies/${id}/config`)
    return response.data
  },

  subscribe: async (data: {
    strategy_id: string
    broker_connection_id?: string
    capital_allocated: number
    is_paper_trading: boolean
    max_drawdown_percent?: number
    daily_loss_limit?: number
    per_trade_stop_loss_percent?: number
    max_positions?: number
    config_params?: Record<string, number | boolean>
    selected_symbols: string[]
    scheduled_start?: string
    scheduled_stop?: string
    active_days?: number[]
  }) => {
    const response = await api.post('/strategies/subscribe', data)
    return response.data
  },

  getMySubscriptions: async () => {
    const response = await api.get('/strategies/subscriptions/my')
    return response.data
  },

  getSubscription: async (subscriptionId: string) => {
    const response = await api.get(`/strategies/subscriptions/${subscriptionId}`)
    return response.data
  },

  updateSubscription: async (subscriptionId: string, data: {
    capital_allocated?: number
    is_paper_trading?: boolean
    max_drawdown_percent?: number
    daily_loss_limit?: number
    per_trade_stop_loss_percent?: number
    max_positions?: number
    config_params?: Record<string, number | boolean>
    selected_symbols?: string[]
    scheduled_start?: string
    scheduled_stop?: string
    active_days?: number[]
  }) => {
    const response = await api.patch(`/strategies/subscriptions/${subscriptionId}`, data)
    return response.data
  },

  subscriptionAction: async (subscriptionId: string, action: 'start' | 'stop' | 'pause' | 'resume') => {
    const response = await api.post(`/strategies/subscriptions/${subscriptionId}/action`, { action })
    return response.data
  },

  unsubscribe: async (subscriptionId: string) => {
    const response = await api.delete(`/strategies/subscriptions/${subscriptionId}`)
    return response.data
  },
}

// Portfolio API
export const portfolioApi = {
  getSummary: async () => {
    const response = await api.get('/portfolio/summary')
    return response.data
  },

  getPositions: async () => {
    const response = await api.get('/portfolio/positions')
    return response.data
  },

  getOrders: async (params?: { page?: number; page_size?: number; status?: string }) => {
    const response = await api.get('/portfolio/orders', { params })
    return response.data
  },

  getTrades: async (params?: { page?: number; page_size?: number; status?: string }) => {
    const response = await api.get('/portfolio/trades', { params })
    return response.data
  },
}

// Reports API
export const reportsApi = {
  getPerformance: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await api.get('/reports/performance', { params })
    return response.data
  },

  downloadTradesCsv: async (params?: { start_date?: string; end_date?: string; subscription_id?: string }) => {
    const response = await api.get('/reports/trades/csv', {
      params,
      responseType: 'blob'
    })
    return response.data
  },

  downloadOrdersCsv: async (params?: { start_date?: string; end_date?: string; subscription_id?: string }) => {
    const response = await api.get('/reports/orders/csv', {
      params,
      responseType: 'blob'
    })
    return response.data
  },

  downloadPortfolioPdf: async () => {
    const response = await api.get('/reports/portfolio/pdf', {
      responseType: 'blob'
    })
    return response.data
  },
}

// Notifications API
export const notificationsApi = {
  getPreferences: async () => {
    const response = await api.get('/notifications/preferences')
    return response.data
  },

  updatePreferences: async (data: {
    email_enabled?: boolean
    sms_enabled?: boolean
    in_app_enabled?: boolean
    trade_alerts?: boolean
    daily_summary?: boolean
    risk_alerts?: boolean
  }) => {
    const response = await api.put('/notifications/preferences', data)
    return response.data
  },
}

// Admin API
export const adminApi = {
  // Strategies
  getStrategies: async (params?: { skip?: number; limit?: number; include_inactive?: boolean }) => {
    const response = await api.get('/admin/strategies', { params })
    return response.data
  },

  createStrategy: async (data: {
    name: string
    slug: string
    description?: string
    long_description?: string
    min_capital?: number
    expected_return_percent?: number
    max_drawdown_percent?: number
    timeframe?: string
    module_path: string
    class_name: string
    is_featured?: boolean
  }) => {
    const response = await api.post('/admin/strategies', data)
    return response.data
  },

  getStrategy: async (id: string) => {
    const response = await api.get(`/admin/strategies/${id}`)
    return response.data
  },

  updateStrategy: async (id: string, data: {
    name?: string
    description?: string
    long_description?: string
    min_capital?: number
    expected_return_percent?: number
    max_drawdown_percent?: number
    is_featured?: boolean
    is_active?: boolean
  }) => {
    const response = await api.patch(`/admin/strategies/${id}`, data)
    return response.data
  },

  deleteStrategy: async (id: string) => {
    const response = await api.delete(`/admin/strategies/${id}`)
    return response.data
  },

  activateStrategy: async (id: string) => {
    const response = await api.post(`/admin/strategies/${id}/activate`)
    return response.data
  },

  getStrategySubscriptions: async (id: string) => {
    const response = await api.get(`/admin/strategies/${id}/subscriptions`)
    return response.data
  },

  getStrategyStats: async (id: string) => {
    const response = await api.get(`/admin/strategies/${id}/stats`)
    return response.data
  },

  // Users
  getUsers: async (params?: { skip?: number; limit?: number; search?: string; is_active?: boolean }) => {
    const response = await api.get('/admin/users', { params })
    return response.data
  },

  getUserStats: async () => {
    const response = await api.get('/admin/users/stats')
    return response.data
  },

  getUser: async (id: string) => {
    const response = await api.get(`/admin/users/${id}`)
    return response.data
  },

  deactivateUser: async (id: string) => {
    const response = await api.post(`/admin/users/${id}/deactivate`)
    return response.data
  },

  activateUser: async (id: string) => {
    const response = await api.post(`/admin/users/${id}/activate`)
    return response.data
  },

  makeAdmin: async (id: string) => {
    const response = await api.post(`/admin/users/${id}/make-admin`)
    return response.data
  },

  removeAdmin: async (id: string) => {
    const response = await api.post(`/admin/users/${id}/remove-admin`)
    return response.data
  },

  // Monitoring
  getDashboard: async () => {
    const response = await api.get('/admin/monitoring/dashboard')
    return response.data
  },

  getActiveStrategies: async () => {
    const response = await api.get('/admin/monitoring/active-strategies')
    return response.data
  },

  getKillSwitchStatus: async () => {
    const response = await api.get('/admin/monitoring/kill-switch/status')
    return response.data
  },

  activateKillSwitch: async (scope: 'global' | 'user' | 'strategy', target_id?: string) => {
    const response = await api.post('/admin/monitoring/kill-switch/activate', { scope, target_id })
    return response.data
  },

  deactivateKillSwitch: async (scope: 'global' | 'user' | 'strategy', target_id?: string) => {
    const response = await api.post('/admin/monitoring/kill-switch/deactivate', { scope, target_id })
    return response.data
  },

  getRecentOrders: async (limit?: number) => {
    const response = await api.get('/admin/monitoring/recent-orders', { params: { limit } })
    return response.data
  },

  getRecentTrades: async (limit?: number) => {
    const response = await api.get('/admin/monitoring/recent-trades', { params: { limit } })
    return response.data
  },

  // Blog Categories
  getBlogCategories: async (includeInactive?: boolean) => {
    const response = await api.get('/admin/blog/categories', {
      params: { include_inactive: includeInactive },
    })
    return response.data
  },

  createBlogCategory: async (data: {
    name: string
    slug: string
    description?: string
    color?: string
    display_order?: number
  }) => {
    const response = await api.post('/admin/blog/categories', data)
    return response.data
  },

  updateBlogCategory: async (id: string, data: {
    name?: string
    slug?: string
    description?: string
    color?: string
    is_active?: boolean
    display_order?: number
  }) => {
    const response = await api.patch(`/admin/blog/categories/${id}`, data)
    return response.data
  },

  deleteBlogCategory: async (id: string) => {
    const response = await api.delete(`/admin/blog/categories/${id}`)
    return response.data
  },

  // Blog Posts
  getBlogPosts: async (params?: {
    skip?: number
    limit?: number
    status?: string
    category_id?: string
    search?: string
  }) => {
    const response = await api.get('/admin/blog/posts', { params })
    return response.data
  },

  getBlogPostsCount: async (params?: {
    status?: string
    category_id?: string
  }) => {
    const response = await api.get('/admin/blog/posts/count', { params })
    return response.data
  },

  getBlogPost: async (id: string) => {
    const response = await api.get(`/admin/blog/posts/${id}`)
    return response.data
  },

  createBlogPost: async (data: {
    title: string
    slug: string
    excerpt?: string
    content: string
    featured_image?: string
    featured_image_alt?: string
    category_id?: string
    tags?: string[]
    author_name?: string
    reading_time_minutes?: number
    meta_title?: string
    meta_description?: string
    meta_keywords?: string[]
    canonical_url?: string
    status?: string
  }) => {
    const response = await api.post('/admin/blog/posts', data)
    return response.data
  },

  updateBlogPost: async (id: string, data: {
    title?: string
    slug?: string
    excerpt?: string
    content?: string
    featured_image?: string
    featured_image_alt?: string
    category_id?: string
    tags?: string[]
    author_name?: string
    reading_time_minutes?: number
    meta_title?: string
    meta_description?: string
    meta_keywords?: string[]
    canonical_url?: string
    status?: string
  }) => {
    const response = await api.patch(`/admin/blog/posts/${id}`, data)
    return response.data
  },

  deleteBlogPost: async (id: string) => {
    const response = await api.delete(`/admin/blog/posts/${id}`)
    return response.data
  },

  publishBlogPost: async (id: string) => {
    const response = await api.post(`/admin/blog/posts/${id}/publish`)
    return response.data
  },

  unpublishBlogPost: async (id: string) => {
    const response = await api.post(`/admin/blog/posts/${id}/unpublish`)
    return response.data
  },

  bulkUploadBlogPosts: async (data: { posts: Array<{
    title: string
    slug: string
    excerpt?: string
    content: string
    featured_image?: string
    featured_image_alt?: string
    category_slug?: string
    tags?: string[]
    author_name?: string
    reading_time_minutes?: number
    meta_title?: string
    meta_description?: string
    meta_keywords?: string[]
    status?: string
  }> }) => {
    const response = await api.post('/admin/blog/posts/bulk', data)
    return response.data
  },

  uploadBlogImage: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/admin/blog/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// Market API
export const marketApi = {
  getIndices: async () => {
    const response = await api.get('/market/indices')
    return response.data
  },

  getHistoricalData: async (params: {
    symbol: string
    exchange?: string
    interval?: string
    start_date: string
    end_date: string
  }) => {
    const response = await api.get(`/market/historical/${params.symbol}`, {
      params: {
        exchange: params.exchange,
        interval: params.interval,
        start_date: params.start_date,
        end_date: params.end_date,
      },
    })
    return response.data
  },

  searchSymbols: async (query: string, exchange?: string) => {
    const response = await api.get('/market/symbols/search', {
      params: { query, exchange },
    })
    return response.data
  },

  getPopularSymbols: async (exchange?: string, limit?: number) => {
    const response = await api.get('/market/symbols/popular', {
      params: { exchange, limit },
    })
    return response.data
  },

  getChartData: async (params: {
    symbol: string
    subscription_id: string
    exchange?: string
    interval?: string
    from_date?: Date
    to_date?: Date
    limit?: number
  }) => {
    const queryParams: Record<string, string | number> = {
      subscription_id: params.subscription_id,
    }

    if (params.exchange) queryParams.exchange = params.exchange
    if (params.interval) queryParams.interval = params.interval
    if (params.from_date) queryParams.from_date = params.from_date.toISOString().split('T')[0]
    if (params.to_date) queryParams.to_date = params.to_date.toISOString().split('T')[0]
    if (params.limit) queryParams.limit = params.limit

    const response = await api.get(`/market/chart/${params.symbol}`, {
      params: queryParams,
    })
    return response.data
  },
}

// Backtest API
export const backtestApi = {
  run: async (data: {
    strategy_id: string
    symbol: string
    exchange?: string
    interval?: string
    start_date: string
    end_date: string
    initial_capital: number
    config?: Record<string, unknown>
  }) => {
    const response = await api.post('/backtest/run', data)
    return response.data
  },

  get: async (backtestId: string) => {
    const response = await api.get(`/backtest/${backtestId}`)
    return response.data
  },

  getStatus: async (backtestId: string) => {
    const response = await api.get(`/backtest/${backtestId}/status`)
    return response.data
  },

  getResults: async (backtestId: string) => {
    const response = await api.get(`/backtest/${backtestId}/results`)
    return response.data
  },

  getTrades: async (backtestId: string, params?: { page?: number; page_size?: number }) => {
    const response = await api.get(`/backtest/${backtestId}/trades`, { params })
    return response.data
  },

  getChartData: async (backtestId: string) => {
    const response = await api.get(`/backtest/${backtestId}/chart-data`)
    return response.data
  },

  getHistory: async (params?: {
    skip?: number
    limit?: number
    status?: string
    strategy_id?: string
  }) => {
    const response = await api.get('/backtest/history', { params })
    return response.data
  },

  subscribeFromBacktest: async (backtestId: string, data: {
    capital_allocated: number
    broker_connection_id?: string
    is_paper_trading?: boolean
    max_drawdown_percent?: number
    daily_loss_limit?: number
    per_trade_stop_loss_percent?: number
    max_positions?: number
  }) => {
    const response = await api.post(`/backtest/${backtestId}/subscribe`, data)
    return response.data
  },

  delete: async (backtestId: string) => {
    const response = await api.delete(`/backtest/${backtestId}`)
    return response.data
  },
}

// Broker API
export const brokerApi = {
  // List all available broker plugins
  listAvailable: async () => {
    const response = await api.get('/broker/available')
    return response.data
  },

  // Get user's broker connections
  getConnections: async () => {
    const response = await api.get('/users/me/broker-connections')
    return response.data
  },

  // Get detailed broker information
  getInfo: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/info`)
    return response.data
  },

  // Get OAuth login URL (for OAuth brokers)
  getLoginUrl: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/login`)
    return response.data
  },

  // Connect with API key (for non-OAuth brokers)
  connect: async (brokerName: string, data: { api_key: string; api_secret: string; totp?: string }) => {
    const response = await api.post(`/broker/${brokerName}/connect`, data)
    return response.data
  },

  // Get broker connection status
  getStatus: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/status`)
    return response.data
  },

  // Get broker profile and account info
  getProfile: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/profile`)
    return response.data
  },

  // Disconnect from broker
  disconnect: async (brokerName: string) => {
    const response = await api.post(`/broker/${brokerName}/disconnect`)
    return response.data
  },

  // Save OAuth broker credentials (APP_ID and Secret Key)
  saveCredentials: async (brokerName: string, data: { app_id: string; secret_key: string }) => {
    const response = await api.post(`/broker/${brokerName}/save-credentials`, data)
    return response.data
  },

  // Get redirect URI for broker configuration
  getRedirectUri: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/redirect-uri`)
    return response.data
  },

  // Get credentials status (whether user has saved credentials)
  getCredentialsStatus: async (brokerName: string) => {
    const response = await api.get(`/broker/${brokerName}/credentials-status`)
    return response.data
  },
}

// Blog API (Public)
export const blogApi = {
  getPosts: async (params?: {
    skip?: number
    limit?: number
    category?: string
    tag?: string
    search?: string
  }) => {
    const response = await api.get('/blog/posts', { params })
    return response.data
  },

  getPostsCount: async (params?: {
    category?: string
    tag?: string
    search?: string
  }) => {
    const response = await api.get('/blog/posts/count', { params })
    return response.data
  },

  getPost: async (slug: string) => {
    const response = await api.get(`/blog/posts/${slug}`)
    return response.data
  },

  getCategories: async (includeEmpty?: boolean) => {
    const response = await api.get('/blog/categories', {
      params: { include_empty: includeEmpty },
    })
    return response.data
  },

  getTags: async () => {
    const response = await api.get('/blog/tags')
    return response.data
  },
}

// Optimization API
export const optimizationApi = {
  run: async (data: {
    source_backtest_id: string
    parameter_ranges: Record<string, { min: number; max: number; step: number }>
    num_samples: number
    objective_metric: string
  }) => {
    const response = await api.post('/optimization/run', data)
    return response.data
  },

  get: async (optimizationId: string) => {
    const response = await api.get(`/optimization/${optimizationId}`)
    return response.data
  },

  getStatus: async (optimizationId: string) => {
    const response = await api.get(`/optimization/${optimizationId}/status`)
    return response.data
  },

  getResults: async (optimizationId: string) => {
    const response = await api.get(`/optimization/${optimizationId}/results`)
    return response.data
  },

  getHeatmap: async (
    optimizationId: string,
    paramX: string,
    paramY: string,
    metric?: string
  ) => {
    const response = await api.get(`/optimization/${optimizationId}/heatmap`, {
      params: { param_x: paramX, param_y: paramY, metric },
    })
    return response.data
  },

  getHistory: async (params?: { skip?: number; limit?: number }) => {
    const response = await api.get('/optimization/history', { params })
    return response.data
  },

  delete: async (optimizationId: string) => {
    const response = await api.delete(`/optimization/${optimizationId}`)
    return response.data
  },
}

// Order Logs API
export const orderLogsApi = {
  getOrderLogs: async (params?: {
    subscription_id?: string
    event_type?: string
    is_dry_run?: boolean
    is_test_order?: boolean
    success?: boolean
    from_date?: string
    to_date?: string
    page?: number
    page_size?: number
  }) => {
    const response = await api.get('/order-logs', { params })
    return response.data
  },

  getOrderLog: async (logId: string) => {
    const response = await api.get(`/order-logs/${logId}`)
    return response.data
  },

  testBrokerOrder: async (data: {
    broker_connection_id: string
    symbol: string
    exchange: string
    transaction_type: 'BUY' | 'SELL'
    quantity: number
    order_type: 'MARKET' | 'LIMIT'
    price?: number
  }) => {
    const response = await api.post('/order-logs/test-broker-order', data)
    return response.data
  },
}
