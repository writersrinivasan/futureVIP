import apiClient from './api'
import type { DashboardMetrics, AdminStats } from '@/types'

export const analyticsService = {
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await apiClient.get('/analytics/dashboard')
    return response.data
  },

  async getAdminStats(): Promise<AdminStats> {
    const response = await apiClient.get('/admin/stats')
    return response.data
  },

  async refreshJobs(): Promise<{ task_id: string; message: string }> {
    const response = await apiClient.post('/admin/jobs/refresh')
    return response.data
  },

  async getAuditLogs(params?: {
    page?: number
    per_page?: number
    action?: string
  }): Promise<{ logs: AdminStats['recent_audit_logs']; total: number }> {
    const response = await apiClient.get('/admin/audit-logs', { params })
    return response.data
  },
}
