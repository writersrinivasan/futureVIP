// ============================================================
// AUTH TYPES
// ============================================================

export interface User {
  id: string
  email: string
  full_name: string
  avatar_url?: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  updated_at: string
  profile?: UserProfile
}

export interface UserProfile {
  current_role?: string
  target_role?: string
  years_experience?: number
  location?: string
  desired_salary_min?: number
  desired_salary_max?: number
  preferred_locations?: string[]
  remote_preference?: 'remote' | 'hybrid' | 'onsite' | 'any'
  skills?: string[]
  bio?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  confirm_password: string
}

// ============================================================
// RESUME TYPES
// ============================================================

export interface Resume {
  id: string
  user_id: string
  filename: string
  file_url: string
  version: number
  is_primary: boolean
  created_at: string
  updated_at: string
  ats_score?: number
  analysis?: ResumeAnalysis
}

export interface ResumeAnalysis {
  id: string
  resume_id: string
  ats_score: ATSScore
  career_trajectory: string
  seniority_level: string
  years_experience: number
  value_proposition: string
  skill_clusters: SkillCluster[]
  red_flags: string[]
  achievements: string[]
  suggested_roles: string[]
  created_at: string
}

export interface ATSScore {
  overall: number
  keyword_match: number
  format_score: number
  readability_score: number
  section_completeness: number
  matching_keywords: string[]
  missing_keywords: string[]
  suggestions: string[]
  optimized_content?: string
}

export interface SkillCluster {
  category: string
  skills: string[]
  proficiency_level: 'beginner' | 'intermediate' | 'advanced' | 'expert'
}

// ============================================================
// JOB TYPES
// ============================================================

export interface Job {
  id: string
  title: string
  company: string
  location: string
  job_type: 'full-time' | 'part-time' | 'contract' | 'internship' | 'freelance'
  remote_type: 'remote' | 'hybrid' | 'onsite'
  salary_min?: number
  salary_max?: number
  currency: string
  description: string
  requirements: string[]
  nice_to_have: string[]
  skills_required: string[]
  posted_at: string
  expires_at?: string
  source: string
  source_url: string
  company_logo?: string
  company_size?: string
  industry?: string
  benefits?: string[]
  created_at: string
}

export interface JobMatch {
  job: Job
  overall_score: number
  embedding_similarity: number
  skill_overlap: number
  experience_alignment: number
  location_match: number
  matched_skills: string[]
  missing_skills: string[]
  salary_match?: boolean
  discovered_at: string
}

export interface JobSearchParams {
  query?: string
  location?: string
  job_type?: string
  remote_type?: string
  salary_min?: number
  salary_max?: number
  source?: string
  skills?: string[]
  sort_by?: 'match_score' | 'date' | 'salary' | 'relevance'
  page?: number
  per_page?: number
}

// ============================================================
// APPLICATION TYPES
// ============================================================

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'screening'
  | 'interview'
  | 'offer'
  | 'accepted'
  | 'rejected'
  | 'withdrawn'

export interface Application {
  id: string
  user_id: string
  job_id: string
  job: Job
  status: ApplicationStatus
  applied_at?: string
  notes?: string
  cover_letter?: string
  resume_id?: string
  match_score?: number
  next_step?: string
  follow_up_date?: string
  salary_offered?: number
  created_at: string
  updated_at: string
}

export interface ApplicationStats {
  total: number
  by_status: Record<ApplicationStatus, number>
  response_rate: number
  interview_rate: number
  offer_rate: number
  avg_match_score: number
}

// ============================================================
// NOTIFICATION TYPES
// ============================================================

export type NotificationType =
  | 'job_match'
  | 'application_update'
  | 'resume_analyzed'
  | 'interview_reminder'
  | 'career_insight'
  | 'system'

export interface Notification {
  id: string
  user_id: string
  type: NotificationType
  title: string
  message: string
  is_read: boolean
  action_url?: string
  metadata?: Record<string, unknown>
  created_at: string
}

// ============================================================
// CAREER TYPES
// ============================================================

export interface CareerRoadmap {
  id: string
  user_id: string
  current_role: string
  target_role: string
  estimated_timeline_months: number
  milestones: RoadmapMilestone[]
  skill_gaps: SkillGap[]
  created_at: string
  updated_at: string
}

export interface RoadmapMilestone {
  id: string
  title: string
  description: string
  timeline_days: number
  is_completed: boolean
  skills_to_learn: string[]
  resources: Resource[]
  completed_at?: string
}

export interface Resource {
  title: string
  url: string
  type: 'course' | 'book' | 'article' | 'video' | 'project' | 'certification'
  platform?: string
  is_free: boolean
  duration_hours?: number
}

export interface SkillGap {
  skill: string
  current_level: number
  required_level: number
  priority: 'high' | 'medium' | 'low'
  resources: Resource[]
}

export interface CareerInsight {
  id: string
  type: 'market_trend' | 'salary_data' | 'opportunity' | 'competition'
  title: string
  description: string
  data?: Record<string, unknown>
  relevance_score: number
  created_at: string
}

// ============================================================
// INTERVIEW TYPES
// ============================================================

export interface InterviewSession {
  id: string
  user_id: string
  job_id?: string
  job_title?: string
  company?: string
  session_type: 'technical' | 'behavioral' | 'mixed' | 'case'
  difficulty: 'easy' | 'medium' | 'hard'
  status: 'active' | 'completed' | 'paused'
  total_questions: number
  answered_questions: number
  overall_score?: number
  started_at: string
  completed_at?: string
  questions: InterviewQuestion[]
}

export interface InterviewQuestion {
  id: string
  session_id: string
  question_text: string
  question_type: 'technical' | 'behavioral' | 'situational' | 'case'
  difficulty: 'easy' | 'medium' | 'hard'
  category?: string
  order: number
  answer?: string
  feedback?: InterviewFeedback
  answered_at?: string
}

export interface InterviewFeedback {
  score: number
  strengths: string[]
  improvements: string[]
  example_answer: string
  star_breakdown?: STARBreakdown
  keywords_used: string[]
  missing_keywords: string[]
}

export interface STARBreakdown {
  situation: { present: boolean; quality: number }
  task: { present: boolean; quality: number }
  action: { present: boolean; quality: number }
  result: { present: boolean; quality: number }
}

// ============================================================
// DASHBOARD TYPES
// ============================================================

export interface DashboardMetrics {
  ats_score: number
  resume_score: number
  avg_match_score: number
  career_progress: number
  saved_jobs: number
  applied_jobs: number
  weekly_opportunities: number
  skill_gaps_count: number
  applications_this_week: number
  interviews_scheduled: number
  profile_completeness: number
  top_job_matches: JobMatch[]
  recent_applications: Application[]
  skill_gap_data: SkillGapRadarData[]
  match_score_distribution: MatchScoreDistribution[]
  application_funnel: ApplicationFunnelData[]
  activity_timeline: ActivityItem[]
}

export interface SkillGapRadarData {
  skill: string
  current: number
  required: number
}

export interface MatchScoreDistribution {
  range: string
  count: number
}

export interface ApplicationFunnelData {
  stage: string
  count: number
  conversion_rate?: number
}

export interface ActivityItem {
  id: string
  type: 'application' | 'match' | 'resume_update' | 'interview' | 'offer'
  title: string
  description: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// ============================================================
// AGENT & TASK TYPES
// ============================================================

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface AgentState {
  task_id: string
  agent_type: string
  status: TaskStatus
  progress: number
  current_step?: string
  result?: unknown
  error?: string
  started_at: string
  updated_at: string
}

// ============================================================
// UTILITY TYPES
// ============================================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ApiError {
  message: string
  code?: string
  details?: Record<string, string[]>
}

export interface SelectOption {
  value: string
  label: string
}

export interface AdminStats {
  total_users: number
  active_users: number
  total_jobs: number
  total_applications: number
  total_resumes: number
  jobs_discovered_today: number
  system_health: SystemHealth
  recent_audit_logs: AuditLog[]
}

export interface SystemHealth {
  api_status: 'healthy' | 'degraded' | 'down'
  database_status: 'healthy' | 'degraded' | 'down'
  ai_service_status: 'healthy' | 'degraded' | 'down'
  job_discovery_status: 'healthy' | 'degraded' | 'down'
  last_job_discovery: string
  queue_size: number
}

export interface AuditLog {
  id: string
  user_id?: string
  user_email?: string
  action: string
  resource: string
  details?: Record<string, unknown>
  ip_address?: string
  created_at: string
}
