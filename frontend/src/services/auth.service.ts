import apiClient from './api'
import type { AuthTokens, LoginRequest, RegisterRequest, User } from '@/types'

export const authService = {
  async login(data: LoginRequest): Promise<AuthTokens> {
    const response = await apiClient.post('/auth/login', {
      email: data.email,
      password: data.password,
    })
    return response.data
  },

  async register(data: RegisterRequest): Promise<User> {
    const response = await apiClient.post('/auth/register', {
      email: data.email,
      password: data.password,
      full_name: data.full_name,
    })
    return response.data
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // Always clear local state even if server call fails
    }
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await apiClient.patch('/auth/me', data)
    return response.data
  },

  async changePassword(data: { current_password: string; new_password: string }): Promise<void> {
    await apiClient.post('/auth/change-password', data)
  },

  async deleteAccount(): Promise<void> {
    await apiClient.delete('/auth/me')
  },
}
