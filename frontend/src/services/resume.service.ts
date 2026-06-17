import apiClient from './api'
import type { Resume, ResumeAnalysis, ATSScore, PaginatedResponse } from '@/types'

export const resumeService = {
  async uploadResume(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<Resume> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/resumes/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })
    return response.data
  },

  async getResumes(): Promise<PaginatedResponse<Resume>> {
    const response = await apiClient.get('/resumes')
    return response.data
  },

  async getResume(id: string): Promise<Resume> {
    const response = await apiClient.get(`/resumes/${id}`)
    return response.data
  },

  async analyzeResume(id: string): Promise<ResumeAnalysis> {
    const response = await apiClient.post(`/resumes/${id}/analyze`)
    return response.data
  },

  async getATSScore(id: string, jobDescription?: string): Promise<ATSScore> {
    const response = await apiClient.post(`/resumes/${id}/ats-score`, {
      job_description: jobDescription,
    })
    return response.data
  },

  async optimizeResume(id: string, jobDescription: string): Promise<{ optimized_content: string; ats_score: ATSScore }> {
    const response = await apiClient.post(`/resumes/${id}/optimize`, {
      job_description: jobDescription,
    })
    return response.data
  },

  async deleteResume(id: string): Promise<void> {
    await apiClient.delete(`/resumes/${id}`)
  },

  async setPrimary(id: string): Promise<Resume> {
    const response = await apiClient.post(`/resumes/${id}/set-primary`)
    return response.data
  },

  async downloadResume(id: string): Promise<Blob> {
    const response = await apiClient.get(`/resumes/${id}/download`, {
      responseType: 'blob',
    })
    return response.data
  },
}
