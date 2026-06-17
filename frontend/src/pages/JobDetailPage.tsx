import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  MapPin,
  DollarSign,
  Calendar,
  Building2,
  Bookmark,
  Zap,
  Wand2,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { jobsService } from '@/services/jobs.service'
import { applicationsService } from '@/services/applications.service'
import { JobMatchScore } from '@/components/jobs/JobMatchScore'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { formatSalaryRange, formatDate } from '@/utils/format'
import type { JobMatch } from '@/types'

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)
  const [optimizeOpen, setOptimizeOpen] = useState(false)
  const [jobDescInput, setJobDescInput] = useState('')

  const jobQuery = useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsService.getJob(id!),
    enabled: !!id,
  })

  const matchQuery = useQuery({
    queryKey: ['job-match', id],
    queryFn: () =>
      jobsService.getJobMatches({ min_score: 0, per_page: 100 }).then((res) =>
        res.items.find((m) => m.job.id === id) ?? null
      ),
    enabled: !!id,
  })

  const companyIntelQuery = useQuery({
    queryKey: ['company-intel', jobQuery.data?.company],
    queryFn: () => jobsService.getCompanyIntelligence(jobQuery.data!.company),
    enabled: !!jobQuery.data?.company,
  })

  const applyMutation = useMutation({
    mutationFn: () =>
      applicationsService.createApplication({ job_id: id!, status: 'applied' }),
    onSuccess: () => {
      toast.success('Application created!')
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      navigate('/applications')
    },
    onError: () => toast.error('Failed to create application'),
  })

  const saveMutation = useMutation({
    mutationFn: () => saved ? jobsService.unsaveJob(id!) : jobsService.saveJob(id!),
    onSuccess: () => {
      setSaved((v) => !v)
      toast.success(saved ? 'Removed from saved' : 'Job saved!')
    },
  })

  const job = jobQuery.data
  const match = matchQuery.data as JobMatch | null

  if (jobQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-32 rounded-lg" />
        <Skeleton className="h-40 rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <Skeleton className="lg:col-span-3 h-96 rounded-xl" />
          <Skeleton className="lg:col-span-2 h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="text-center py-20 text-slate-400">
        Job not found.{' '}
        <button onClick={() => navigate('/jobs')} className="text-indigo-400 underline">
          Back to jobs
        </button>
      </div>
    )
  }

  const remoteVariant = {
    remote: 'success',
    hybrid: 'warning',
    onsite: 'default',
  } as const

  return (
    <div className="space-y-4 pb-6">
      {/* Back button */}
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<ArrowLeft className="w-4 h-4" />}
        onClick={() => navigate(-1)}
        className="w-fit"
      >
        Back to Jobs
      </Button>

      {/* Job header card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-indigo-600/30 to-violet-600/30 border border-white/10 flex items-center justify-center flex-shrink-0">
            {job.company_logo ? (
              <img src={job.company_logo} alt={job.company} className="w-10 h-10 object-contain" />
            ) : (
              <Building2 className="w-7 h-7 text-indigo-400" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-white mb-1">{job.title}</h1>
            <p className="text-slate-400 font-medium mb-3">{job.company}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-slate-400">
              {job.location && (
                <span className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5" />
                  {job.location}
                </span>
              )}
              {(job.salary_min || job.salary_max) && (
                <span className="flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5" />
                  {formatSalaryRange(job.salary_min, job.salary_max, job.currency)}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                Posted {formatDate(job.posted_at)}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <Badge variant={remoteVariant[job.remote_type] ?? 'default'} size="sm">
                {job.remote_type}
              </Badge>
              <Badge variant="primary" size="sm">{job.job_type}</Badge>
              {job.industry && <Badge variant="outline" size="sm">{job.industry}</Badge>}
            </div>
          </div>
          <div className="flex flex-row sm:flex-col gap-2 flex-shrink-0">
            <Button
              variant="primary"
              size="md"
              leftIcon={<Zap className="w-4 h-4" />}
              isLoading={applyMutation.isPending}
              onClick={() => applyMutation.mutate()}
            >
              Quick Apply
            </Button>
            <Button
              variant={saved ? 'secondary' : 'outline'}
              size="md"
              leftIcon={<Bookmark className={saved ? 'w-4 h-4 fill-current' : 'w-4 h-4'} />}
              onClick={() => saveMutation.mutate()}
            >
              {saved ? 'Saved' : 'Save'}
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: description */}
        <div className="lg:col-span-3 space-y-4">
          {/* Description */}
          <div className="glass-card p-5">
            <h2 className="text-base font-semibold text-slate-200 mb-3">Job Description</h2>
            <div
              className="text-sm text-slate-300 leading-relaxed prose prose-invert prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: job.description }}
            />
          </div>

          {/* Requirements */}
          {job.requirements.length > 0 && (
            <div className="glass-card p-5">
              <h2 className="text-base font-semibold text-slate-200 mb-3">Requirements</h2>
              <ul className="space-y-2">
                {job.requirements.map((req, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0 mt-1.5" />
                    {req}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Nice to have */}
          {job.nice_to_have.length > 0 && (
            <div className="glass-card p-5">
              <h2 className="text-base font-semibold text-slate-200 mb-3">Nice to Have</h2>
              <ul className="space-y-2">
                {job.nice_to_have.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500 flex-shrink-0 mt-1.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Optimize CTA */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-300">Optimize Resume for This Job</h3>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Wand2 className="w-3.5 h-3.5" />}
                onClick={() => setOptimizeOpen((v) => !v)}
              >
                Optimize
              </Button>
            </div>
            {optimizeOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
              >
                <p className="text-xs text-slate-400 mb-3">
                  The job description will be pre-filled. Go to Resume page to run optimization.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/resume')}
                >
                  Go to Resume Optimizer →
                </Button>
              </motion.div>
            )}
          </div>
        </div>

        {/* Right: match score + company */}
        <div className="lg:col-span-2 space-y-4">
          {/* Match score */}
          {match && (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-slate-300 mb-4">Match Analysis</h3>
              <JobMatchScore match={match} />
            </div>
          )}

          {/* Company intelligence */}
          <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-slate-400" />
              Company Intelligence
            </h3>
            {companyIntelQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ) : companyIntelQuery.data ? (
              <div className="space-y-3">
                <p className="text-sm text-slate-300 leading-relaxed">
                  {companyIntelQuery.data.overview}
                </p>
                {companyIntelQuery.data.size && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span className="font-medium text-slate-300">Size:</span>
                    {companyIntelQuery.data.size}
                  </div>
                )}
                {companyIntelQuery.data.culture && (
                  <p className="text-xs text-slate-400 italic">
                    "{companyIntelQuery.data.culture}"
                  </p>
                )}
                {companyIntelQuery.data.tech_stack && companyIntelQuery.data.tech_stack.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-400 mb-1.5">Tech Stack</p>
                    <div className="flex flex-wrap gap-1.5">
                      {companyIntelQuery.data.tech_stack.map((tech) => (
                        <Badge key={tech} variant="primary" size="sm">{tech}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No company data available</p>
            )}
          </div>

          {/* Source link */}
          {job.source_url && (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 p-3 rounded-xl border border-white/10 bg-white/3 text-sm text-slate-400 hover:text-white hover:bg-white/8 transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              View on {job.source || 'Source'}
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
