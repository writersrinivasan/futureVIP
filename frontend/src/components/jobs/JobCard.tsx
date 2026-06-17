import { motion } from 'framer-motion'
import { MapPin, Clock, DollarSign, ExternalLink, Bookmark, Zap, Building2 } from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Progress } from '@/components/common/Progress'
import { formatSalaryRange, formatTimeAgo, truncateText } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { JobMatch, Job } from '@/types'

interface JobCardProps {
  job?: Job
  match?: JobMatch
  onApply?: () => void
  onSave?: () => void
  onView?: () => void
  isSaved?: boolean
  index?: number
  compact?: boolean
}

export const JobCard = ({
  job: jobProp,
  match,
  onApply,
  onSave,
  onView,
  isSaved = false,
  index = 0,
  compact = false,
}: JobCardProps) => {
  const job = match?.job || jobProp
  if (!job) return null

  const matchScore = match?.overall_score

  const remoteVariant = {
    remote: 'success',
    hybrid: 'warning',
    onsite: 'default',
  } as const

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="glass-card p-4 hover:bg-white/8 hover:border-white/20 transition-all duration-300 cursor-pointer"
      onClick={onView}
    >
      <div className="flex gap-3">
        {/* Company Logo Placeholder */}
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-600/30 to-secondary-600/30 border border-white/10 flex items-center justify-center flex-shrink-0">
          {job.company_logo ? (
            <img src={job.company_logo} alt={job.company} className="w-8 h-8 object-contain" />
          ) : (
            <Building2 className="w-5 h-5 text-primary-400" />
          )}
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-200 truncate hover:text-primary-300 transition-colors">
                {job.title}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{job.company}</p>
            </div>

            {/* Match Score Badge */}
            {matchScore !== undefined && (
              <div
                className={cn(
                  'flex-shrink-0 text-xs font-bold px-2.5 py-1 rounded-full',
                  matchScore >= 80
                    ? 'bg-success-500/20 text-success-300'
                    : matchScore >= 60
                    ? 'bg-primary-500/20 text-primary-300'
                    : 'bg-slate-500/20 text-slate-400'
                )}
              >
                {Math.round(matchScore)}% match
              </div>
            )}
          </div>

          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-slate-500">
            {job.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {job.location}
              </span>
            )}
            {(job.salary_min || job.salary_max) && (
              <span className="flex items-center gap-1">
                <DollarSign className="w-3 h-3" />
                {formatSalaryRange(job.salary_min, job.salary_max)}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTimeAgo(job.posted_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        <Badge variant={remoteVariant[job.remote_type] || 'default'} size="sm">
          {job.remote_type}
        </Badge>
        <Badge variant="default" size="sm">
          {job.job_type}
        </Badge>
        {job.source && (
          <Badge variant="outline" size="sm">{job.source}</Badge>
        )}
        {match?.matched_skills.slice(0, 2).map((skill) => (
          <Badge key={skill} variant="accent" size="sm">{skill}</Badge>
        ))}
      </div>

      {/* Match Score Bar */}
      {matchScore !== undefined && (
        <div className="mt-3">
          <Progress
            value={matchScore}
            size="sm"
            animated={false}
            variant={matchScore >= 80 ? 'success' : matchScore >= 60 ? 'primary' : 'danger'}
          />
        </div>
      )}

      {/* Description preview (non-compact) */}
      {!compact && job.description && (
        <p className="text-xs text-slate-500 mt-2 leading-relaxed">
          {truncateText(job.description.replace(/<[^>]*>/g, ''), 120)}
        </p>
      )}

      {/* Actions */}
      <div
        className="flex items-center gap-2 mt-3"
        onClick={(e) => e.stopPropagation()}
      >
        {onApply && (
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Zap className="w-3.5 h-3.5" />}
            onClick={onApply}
            className="flex-1 md:flex-none"
          >
            Apply Now
          </Button>
        )}
        {onSave && (
          <Button
            variant={isSaved ? 'secondary' : 'ghost'}
            size="sm"
            leftIcon={<Bookmark className={cn('w-3.5 h-3.5', isSaved && 'fill-current')} />}
            onClick={onSave}
          >
            {isSaved ? 'Saved' : 'Save'}
          </Button>
        )}
        {onView && (
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ExternalLink className="w-3.5 h-3.5" />}
            onClick={onView}
            className="ml-auto"
          >
            Details
          </Button>
        )}
      </div>
    </motion.div>
  )
}
