import apiClient from './api'
import type { InterviewSession, InterviewQuestion, InterviewFeedback, PaginatedResponse } from '@/types'

export const interviewService = {
  async startSession(data: {
    job_id?: string
    job_title?: string
    company?: string
    session_type: 'technical' | 'behavioral' | 'mixed' | 'case'
    difficulty: 'easy' | 'medium' | 'hard'
    num_questions?: number
  }): Promise<InterviewSession> {
    const response = await apiClient.post('/interview/sessions', data)
    return response.data
  },

  async getSessions(params?: {
    page?: number
    per_page?: number
    status?: string
  }): Promise<PaginatedResponse<InterviewSession>> {
    const response = await apiClient.get('/interview/sessions', { params })
    return response.data
  },

  async getSession(id: string): Promise<InterviewSession> {
    const response = await apiClient.get(`/interview/sessions/${id}`)
    return response.data
  },

  async getQuestion(sessionId: string, questionIndex?: number): Promise<InterviewQuestion> {
    const response = await apiClient.get(`/interview/sessions/${sessionId}/questions`, {
      params: { index: questionIndex },
    })
    return response.data
  },

  async submitAnswer(
    sessionId: string,
    questionId: string,
    answer: string
  ): Promise<InterviewFeedback> {
    const response = await apiClient.post(
      `/interview/sessions/${sessionId}/questions/${questionId}/answer`,
      { answer }
    )
    return response.data
  },

  async getFeedback(sessionId: string): Promise<{
    overall_score: number
    session_feedback: string
    strengths: string[]
    improvements: string[]
    question_feedbacks: Array<{ question_id: string; feedback: InterviewFeedback }>
  }> {
    const response = await apiClient.get(`/interview/sessions/${sessionId}/feedback`)
    return response.data
  },

  async completeSession(sessionId: string): Promise<InterviewSession> {
    const response = await apiClient.post(`/interview/sessions/${sessionId}/complete`)
    return response.data
  },
}
