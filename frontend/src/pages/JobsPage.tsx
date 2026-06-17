import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Search, SlidersHorizontal, RefreshCw, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import { jobsService } from '@/services/jobs.service'
import { applicationsService } from '@/services/applications.service'
import { JobList } from '@/components/jobs/JobList'
import { JobFilters } from '@/components/jobs/JobFilters'
import { Button } from '@/components/common/Button'
import { cn } from '@/utils/cn'
import type { JobSearchParams } from '@/types'

const TABS = [
  { id: 'all', label: 'All Jobs' },
  { id: 'matches', label: 'My Matches' },
] as const

type TabId = typeof TABS[number]['id']

export default function JobsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('all')
  const [query, setQuery] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [filters, setFilters] = useState<JobSearchParams>({ page: 1, per_page: 20 })
  const [page, setPage] = useState(1)

  const jobsQuery = useQuery({
    queryKey: ['jobs', activeTab, query, filters, page],
    queryFn: () => {
      const params: JobSearchParams = { ...filters, page, query: query || undefined }
      if (activeTab === 'matches') {
        return jobsService.getJobMatches({ page, per_page: 20, sort_by: 'match_score' })
          .then((res) => ({
            ...res,
            items: res.items.map((m) => m.job),
            _matches: res.items,
          }))
      }
      return jobsService.getJobs(params)
    },
    placeholderData: (prev) => prev,
  })

  const matchesQuery = useQuery({
    queryKey: ['job-matches', page],
    queryFn: () => jobsService.getJobMatches({ page, per_page: 20, sort_by: 'match_score' }),
    enabled: activeTab === 'matches',
  })

  const discoverMutation = useMutation({
    mutationFn: () => jobsService.discoverJobs(),
    onSuccess: (data) => {
      toast.success(data.message ?? 'Job discovery started!')
    },
    onError: () => toast.error('Failed to start job discovery'),
  })

  const applyMutation = useMutation({
    mutationFn: (jobId: string) =>
      applicationsService.createApplication({ job_id: jobId, status: 'applied' }),
    onSuccess: () => {
      toast.success('Application created!')
      navigate('/applications')
    },
    onError: () => toast.error('Failed to create application'),
  })

  const saveMutation = useMutation({
    mutationFn: (jobId: string) => jobsService.saveJob(jobId),
    onSuccess: () => toast.success('Job saved!'),
    onError: () => toast.error('Failed to save job'),
  })

  const allJobs = jobsQuery.data?.items ?? []
  const matches = matchesQuery.data?.items ?? []
  const matchMap = new Map(matches.map((m) => [m.job.id, m]))

  return (
    <div className="space-y-4 pb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-white">Job Opportunities</h1>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className={cn('w-3.5 h-3.5', discoverMutation.isPending && 'animate-spin')} />}
            isLoading={discoverMutation.isPending}
            onClick={() => discoverMutation.mutate()}
          >
            Discover New Jobs
          </Button>
        </div>
      </div>

      {/* Search + tabs */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search jobs, companies, skills..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1) }}
            className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/30"
          />
        </div>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<SlidersHorizontal className="w-4 h-4" />}
          onClick={() => setFiltersOpen((v) => !v)}
        >
          Filters
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/10">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setPage(1) }}
            className={cn(
              'px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px',
              activeTab === tab.id
                ? 'text-indigo-400 border-indigo-400'
                : 'text-slate-400 border-transparent hover:text-slate-200'
            )}
          >
            {tab.id === 'matches' && (
              <Zap className="w-3.5 h-3.5 inline mr-1.5 text-amber-400" />
            )}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main layout */}
      <div className="flex gap-4">
        {/* Filters sidebar */}
        {filtersOpen && (
          <motion.aside
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="w-72 flex-shrink-0"
          >
            <JobFilters
              filters={filters}
              onFilterChange={(f) => { setFilters(f as JobSearchParams); setPage(1) }}
              onClear={() => { setFilters({ page: 1, per_page: 20 }); setPage(1) }}
            />
          </motion.aside>
        )}

        {/* Job list */}
        <div className="flex-1 min-w-0">
          <JobList
            jobs={allJobs}
            matches={activeTab === 'matches' ? matches : undefined}
            isLoading={jobsQuery.isLoading}
            currentPage={page}
            totalPages={jobsQuery.data?.total_pages ?? 1}
            onPageChange={setPage}
            onApply={(jobId) => applyMutation.mutate(jobId)}
            onSave={(jobId) => saveMutation.mutate(jobId)}
          />
        </div>
      </div>
    </div>
  )
}
