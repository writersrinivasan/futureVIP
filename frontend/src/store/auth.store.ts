import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, AuthTokens } from '@/types'

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (user: User, tokens: AuthTokens) => void
  logout: () => void
  setUser: (user: User) => void
  setTokens: (tokens: AuthTokens) => void
  setLoading: (loading: boolean) => void
  refreshToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,

      login: (user: User, tokens: AuthTokens) => {
        set({ user, tokens, isAuthenticated: true, isLoading: false })
      },

      logout: () => {
        set({ user: null, tokens: null, isAuthenticated: false })
        localStorage.removeItem('auth-storage')
      },

      setUser: (user: User) => {
        set({ user })
      },

      setTokens: (tokens: AuthTokens) => {
        set({ tokens })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      refreshToken: async () => {
        const { tokens } = get()
        if (!tokens?.refresh_token) {
          get().logout()
          return
        }

        try {
          const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: tokens.refresh_token }),
          })

          if (!response.ok) {
            get().logout()
            return
          }

          const newTokens: AuthTokens = await response.json()
          set({ tokens: newTokens })
        } catch {
          get().logout()
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
