import apiClient from './api'
import type { Job, JobMatch, JobSearchParams, PaginatedResponse } from '@/types'

export const jobsService = {
  async getJobs(params?: JobSearchParams): Promise<PaginatedResponse<Job>> {
    const response = await apiClient.get('/jobs', { params })
    return response.data
  },

  async getJob(id: string): Promise<Job> {
    const response = await apiClient.get(`/jobs/${id}`)
    return response.data
  },

  async searchJobs(params: JobSearchParams): Promise<PaginatedResponse<Job>> {
    const response = await apiClient.post('/jobs/search', params)
    return response.data
  },

  async getJobMatches(params?: {
    min_score?: number
    page?: number
    per_page?: number
    sort_by?: string
  }): Promise<PaginatedResponse<JobMatch>> {
    const response = await apiClient.get('/jobs/matches', { params })
    return response.data
  },

  async discoverJobs(): Promise<{ task_id: string; message: string }> {
    const response = await apiClient.post('/jobs/discover')
    return response.data
  },

  async getJobSources(): Promise<{ name: string; count: number; last_updated: string }[]> {
    const response = await apiClient.get('/jobs/sources')
    return response.data
  },

  async saveJob(jobId: string): Promise<void> {
    await apiClient.post(`/jobs/${jobId}/save`)
  },

  async unsaveJob(jobId: string): Promise<void> {
    await apiClient.delete(`/jobs/${jobId}/save`)
  },

  async getCompanyIntelligence(company: string): Promise<{
    overview: string
    culture: string
    size: string
    funding?: string
    tech_stack?: string[]
    interview_tips?: string[]
  }> {
    const response = await apiClient.get('/jobs/company-intel', {
      params: { company },
    })
    return response.data
  },
}
