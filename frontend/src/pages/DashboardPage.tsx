import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart2,
  FileText,
  Zap,
  TrendingUp,
  Bookmark,
  Send,
  Calendar,
  AlertTriangle,
  Upload,
  Search,
  Mic,
} from 'lucide-react'
import { analyticsService } from '@/services/analytics.service'
import { useAuthStore } from '@/store/auth.store'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MatchScoreChart } from '@/components/dashboard/MatchScoreChart'
import { ApplicationFunnel } from '@/components/dashboard/ApplicationFunnel'
import { SkillGapRadar } from '@/components/dashboard/SkillGapRadar'
import { ActivityTimeline } from '@/components/dashboard/ActivityTimeline'
import { ATSGauge } from '@/components/dashboard/ATSGauge'
import { JobCard } from '@/components/jobs/JobCard'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => analyticsService.getDashboardMetrics(),
    staleTime: 1000 * 60 * 3,
  })

  const firstName = user?.full_name?.split(' ')[0] ?? 'there'

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-16 rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <Skeleton className="lg:col-span-3 h-72 rounded-xl" />
          <Skeleton className="lg:col-span-2 h-72 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 pb-6">
      {/* Welcome banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl bg-gradient-to-r from-indigo-500/15 to-violet-500/10 border border-indigo-500/20"
      >
        <div>
          <h1 className="text-xl font-bold text-white mb-1">
            Welcome back, {firstName}! 👋
          </h1>
          <p className="text-sm text-slate-400">
            Here's your career pulse — {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Upload className="w-3.5 h-3.5" />}
            onClick={() => navigate('/resume')}
          >
            Upload Resume
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Search className="w-3.5 h-3.5" />}
            onClick={() => navigate('/jobs')}
          >
            Discover Jobs
          </Button>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Mic className="w-3.5 h-3.5" />}
            onClick={() => navigate('/interview')}
          >
            Interview
          </Button>
        </div>
      </motion.div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard
          icon={<BarChart2 className="w-5 h-5" />}
          value={metrics?.ats_score ?? 0}
          suffix="%"
          label="ATS Score"
          color="primary"
          index={0}
          onClick={() => navigate('/resume')}
        />
        <MetricCard
          icon={<FileText className="w-5 h-5" />}
          value={metrics?.resume_score ?? 0}
          suffix="%"
          label="Resume Score"
          color="secondary"
          index={1}
          onClick={() => navigate('/resume')}
        />
        <MetricCard
          icon={<Zap className="w-5 h-5" />}
          value={metrics?.avg_match_score ? Math.round(metrics.avg_match_score) : 0}
          suffix="%"
          label="Avg Match Score"
          color="accent"
          index={2}
          onClick={() => navigate('/jobs')}
        />
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          value={metrics?.career_progress ?? 0}
          suffix="%"
          label="Career Progress"
          color="success"
          index={3}
          onClick={() => navigate('/career')}
        />
        <MetricCard
          icon={<Bookmark className="w-5 h-5" />}
          value={metrics?.saved_jobs ?? 0}
          label="Saved Jobs"
          color="warning"
          index={4}
          onClick={() => navigate('/jobs')}
        />
        <MetricCard
          icon={<Send className="w-5 h-5" />}
          value={metrics?.applied_jobs ?? 0}
          label="Applied Jobs"
          color="primary"
          index={5}
          onClick={() => navigate('/applications')}
        />
        <MetricCard
          icon={<Calendar className="w-5 h-5" />}
          value={metrics?.weekly_opportunities ?? 0}
          label="New This Week"
          color="secondary"
          index={6}
          onClick={() => navigate('/jobs')}
        />
        <MetricCard
          icon={<AlertTriangle className="w-5 h-5" />}
          value={metrics?.skill_gaps_count ?? 0}
          label="Skill Gaps"
          color="danger"
          index={7}
          onClick={() => navigate('/career')}
        />
      </div>

      {/* ATS gauge + middle charts */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-1">
          <ATSGauge score={metrics?.ats_score ?? 0} />
        </div>
        <div className="lg:col-span-2">
          <MatchScoreChart data={metrics?.match_score_distribution ?? []} />
        </div>
        <div className="lg:col-span-2">
          <ApplicationFunnel data={metrics?.application_funnel ?? []} />
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Skill gap radar */}
        <div>
          <SkillGapRadar data={metrics?.skill_gap_data ?? []} />
        </div>

        {/* Top job matches */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-300">Top Job Matches</h3>
            <button
              onClick={() => navigate('/jobs')}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              View all →
            </button>
          </div>
          <div className="space-y-3">
            {metrics?.top_job_matches && metrics.top_job_matches.length > 0 ? (
              metrics.top_job_matches.slice(0, 3).map((match, i) => (
                <JobCard
                  key={match.job.id}
                  match={match}
                  index={i}
                  compact
                  onView={() => navigate(`/jobs/${match.job.id}`)}
                />
              ))
            ) : (
              <EmptyState
                icon={<Search className="w-5 h-5" />}
                title="No matches yet"
                description="Upload your resume to discover job matches"
                action={{ label: 'Upload Resume', onClick: () => navigate('/resume') }}
              />
            )}
          </div>
        </div>

        {/* Activity timeline */}
        <div>
          <ActivityTimeline activities={metrics?.activity_timeline ?? []} />
        </div>
      </div>
    </div>
  )
}
