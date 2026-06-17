import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/auth.service'
import type { LoginRequest, RegisterRequest } from '@/types'
import toast from 'react-hot-toast'

export const useAuth = () => {
  const navigate = useNavigate()
  const { user, tokens, isAuthenticated, isLoading, login, logout, setLoading, setTokens } = useAuthStore()

  const handleLogin = useCallback(
    async (data: LoginRequest) => {
      setLoading(true)
      try {
        // login() returns AuthTokens only; store them so the interceptor can
        // attach the header for the subsequent getMe() call
        const newTokens = await authService.login(data)
        setTokens(newTokens)
        const me = await authService.getMe()
        login(me, newTokens)
        toast.success(`Welcome back, ${me.full_name.split(' ')[0]}!`)
        navigate('/dashboard')
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        toast.error(error?.response?.data?.detail || 'Login failed. Please check your credentials.')
        throw err
      } finally {
        setLoading(false)
      }
    },
    [login, navigate, setLoading, setTokens]
  )

  const handleRegister = useCallback(
    async (data: RegisterRequest) => {
      setLoading(true)
      try {
        // register() creates the account and returns the User; then login for tokens
        await authService.register(data)
        const newTokens = await authService.login({ email: data.email, password: data.password })
        setTokens(newTokens)
        const me = await authService.getMe()
        login(me, newTokens)
        toast.success(`Welcome to FUTURE VIP, ${me.full_name.split(' ')[0]}!`)
        navigate('/dashboard')
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        toast.error(error?.response?.data?.detail || 'Registration failed. Please try again.')
        throw err
      } finally {
        setLoading(false)
      }
    },
    [login, navigate, setLoading, setTokens]
  )

  const handleLogout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      logout()
      navigate('/login')
      toast.success('Logged out successfully')
    }
  }, [logout, navigate])

  return {
    user,
    tokens,
    isAuthenticated,
    isLoading,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
  }
}
