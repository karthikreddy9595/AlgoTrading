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

  subscribe: async (data: {
    strategy_id: string
    capital_allocated: number
    is_paper_trading: boolean
    max_drawdown_percent?: number
    daily_loss_limit?: number
  }) => {
    const response = await api.post('/strategies/subscribe', data)
    return response.data
  },

  getMySubscriptions: async () => {
    const response = await api.get('/strategies/subscriptions/my')
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
