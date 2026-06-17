import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor: attach Bearer token + user's OpenAI key if configured
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const stored = localStorage.getItem('auth-storage')
    if (stored) {
      try {
        const { state } = JSON.parse(stored)
        if (state?.tokens?.access_token) {
          config.headers.Authorization = `Bearer ${state.tokens.access_token}`
        }
      } catch {
        // ignore parse errors
      }
    }

    // Attach user-provided OpenAI key so backend agents can use it
    const keysStored = localStorage.getItem('keys-storage')
    if (keysStored) {
      try {
        const { state: keysState } = JSON.parse(keysStored)
        if (keysState?.openaiKey) {
          config.headers['X-OpenAI-Api-Key'] = keysState.openaiKey
        }
      } catch {
        // ignore parse errors
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Track if we're refreshing to avoid infinite loops
let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

const processQueue = (token: string) => {
  refreshQueue.forEach((cb) => cb(token))
  refreshQueue = []
}

// Response interceptor: handle 401 and errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(apiClient(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const stored = localStorage.getItem('auth-storage')
      if (stored) {
        try {
          const { state } = JSON.parse(stored)
          const refreshToken = state?.tokens?.refresh_token

          if (refreshToken) {
            const response = await apiClient.post('/auth/refresh', {
              refresh_token: refreshToken,
            })
            const { access_token } = response.data
            const newState = {
              ...state,
              tokens: { ...state.tokens, access_token },
            }
            localStorage.setItem('auth-storage', JSON.stringify({ state: newState }))
            processQueue(access_token)
            isRefreshing = false
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`
            }
            return apiClient(originalRequest)
          }
        } catch {
          isRefreshing = false
          refreshQueue = []
          localStorage.removeItem('auth-storage')
          window.location.href = '/login'
          return Promise.reject(error)
        }
      }

      isRefreshing = false
      localStorage.removeItem('auth-storage')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // Handle other errors
    if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action')
    } else if (error.response?.status === 404) {
      // Let caller handle 404
    } else if (error.response?.status === 500) {
      toast.error('Server error. Please try again later.')
    } else if (error.response?.status === 422) {
      // Validation error - let caller handle
    } else if (!error.response && error.code === 'ERR_NETWORK') {
      toast.error('Network error. Please check your connection.')
    }

    return Promise.reject(error)
  }
)

export default apiClient
