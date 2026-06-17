import apiClient from './api'
import type { CareerRoadmap, SkillGap, CareerInsight } from '@/types'

export const careerService = {
  async getRoadmap(): Promise<CareerRoadmap | null> {
    try {
      const response = await apiClient.get('/career/roadmap')
      return response.data
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } }
      if (error?.response?.status === 404) return null
      throw err
    }
  },

  async generateRoadmap(data: {
    current_role: string
    target_role: string
    timeline_months?: number
  }): Promise<CareerRoadmap> {
    const response = await apiClient.post('/career/roadmap/generate', data)
    return response.data
  },

  async updateMilestone(
    roadmapId: string,
    milestoneId: string,
    data: { is_completed: boolean }
  ): Promise<void> {
    await apiClient.patch(`/career/roadmap/${roadmapId}/milestones/${milestoneId}`, data)
  },

  async getSkills(): Promise<{ skills: string[]; proficiency: Record<string, number> }> {
    const response = await apiClient.get('/career/skills')
    return response.data
  },

  async analyzeSkills(): Promise<SkillGap[]> {
    const response = await apiClient.post('/career/skills/analyze')
    return response.data
  },

  async getCareerInsights(): Promise<CareerInsight[]> {
    const response = await apiClient.get('/career/insights')
    return response.data
  },

  async getMarketData(role: string): Promise<{
    avg_salary: number
    salary_range: { min: number; max: number }
    demand_score: number
    top_skills: string[]
    top_companies: string[]
  }> {
    const response = await apiClient.get('/career/market-data', { params: { role } })
    return response.data
  },
}
