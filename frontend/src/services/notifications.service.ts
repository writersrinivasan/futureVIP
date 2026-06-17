import apiClient from './api'
import type { Notification, PaginatedResponse } from '@/types'

export const notificationsService = {
  async getNotifications(params?: {
    page?: number
    per_page?: number
    type?: string
    is_read?: boolean
  }): Promise<PaginatedResponse<Notification>> {
    const response = await apiClient.get('/notifications', { params })
    return response.data
  },

  async markRead(id: string): Promise<Notification> {
    const response = await apiClient.patch(`/notifications/${id}/read`)
    return response.data
  },

  async markAllRead(): Promise<void> {
    await apiClient.post('/notifications/mark-all-read')
  },

  async deleteNotification(id: string): Promise<void> {
    await apiClient.delete(`/notifications/${id}`)
  },

  async getUnreadCount(): Promise<{ count: number }> {
    const response = await apiClient.get('/notifications/unread-count')
    return response.data
  },
}
