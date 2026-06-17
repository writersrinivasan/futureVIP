import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/auth.service'
import type { LoginRequest, RegisterRequest } from '@/types'
import toast from 'react-hot-toast'

export const useAuth = () => {
  const navigate = useNavigate()
  const { user, tokens, isAuthenticated, isLoading, login, logout, setLoading } = useAuthStore()

  const handleLogin = useCallback(
    async (data: LoginRequest) => {
      setLoading(true)
      try {
        const result = await authService.login(data)
        login(result.user, result.tokens)
        toast.success(`Welcome back, ${result.user.full_name.split(' ')[0]}!`)
        navigate('/dashboard')
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        const message = error?.response?.data?.detail || 'Login failed. Please check your credentials.'
        toast.error(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [login, navigate, setLoading]
  )

  const handleRegister = useCallback(
    async (data: RegisterRequest) => {
      setLoading(true)
      try {
        const result = await authService.register(data)
        login(result.user, result.tokens)
        toast.success(`Welcome to FUTURE VIP, ${result.user.full_name.split(' ')[0]}!`)
        navigate('/dashboard')
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } }
        const message = error?.response?.data?.detail || 'Registration failed. Please try again.'
        toast.error(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [login, navigate, setLoading]
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
