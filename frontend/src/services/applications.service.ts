import apiClient from './api'
import type { Application, ApplicationStatus, ApplicationStats, PaginatedResponse } from '@/types'

export const applicationsService = {
  async createApplication(data: {
    job_id: string
    status?: ApplicationStatus
    notes?: string
    cover_letter?: string
    resume_id?: string
  }): Promise<Application> {
    const response = await apiClient.post('/applications', data)
    return response.data
  },

  async getApplications(params?: {
    status?: ApplicationStatus
    page?: number
    per_page?: number
    sort_by?: string
  }): Promise<PaginatedResponse<Application>> {
    const response = await apiClient.get('/applications', { params })
    return response.data
  },

  async getApplication(id: string): Promise<Application> {
    const response = await apiClient.get(`/applications/${id}`)
    return response.data
  },

  async updateApplication(
    id: string,
    data: Partial<{
      status: ApplicationStatus
      notes: string
      cover_letter: string
      next_step: string
      follow_up_date: string
      salary_offered: number
    }>
  ): Promise<Application> {
    const response = await apiClient.patch(`/applications/${id}`, data)
    return response.data
  },

  async deleteApplication(id: string): Promise<void> {
    await apiClient.delete(`/applications/${id}`)
  },

  async getApplicationStats(): Promise<ApplicationStats> {
    const response = await apiClient.get('/applications/stats')
    return response.data
  },

  async generateCoverLetter(applicationId: string): Promise<{ cover_letter: string }> {
    const response = await apiClient.post(`/applications/${applicationId}/cover-letter`)
    return response.data
  },
}
