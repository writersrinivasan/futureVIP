import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { JobCard } from './JobCard'
import { JobCardSkeleton, Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/common/Button'
import { Briefcase, ChevronLeft, ChevronRight } from 'lucide-react'
import type { Job, JobMatch } from '@/types'

interface JobListProps {
  jobs?: Job[]
  matches?: JobMatch[]
  isLoading?: boolean
  totalPages?: number
  currentPage?: number
  onPageChange?: (page: number) => void
  onApply?: (jobId: string) => void
  onSave?: (jobId: string) => void
  emptyTitle?: string
  emptyDescription?: string
}

export const JobList = ({
  jobs,
  matches,
  isLoading,
  totalPages = 1,
  currentPage = 1,
  onPageChange,
  onApply,
  onSave,
  emptyTitle = 'No jobs found',
  emptyDescription = 'Try adjusting your filters or check back later',
}: JobListProps) => {
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  const items = matches || jobs?.map((job) => ({ job })) || []

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Briefcase className="w-8 h-8" />}
        title={emptyTitle}
        description={emptyDescription}
      />
    )
  }

  return (
    <div className="space-y-3">
      {/* Job cards */}
      {items.map((item, index) => {
        const job = 'job' in item ? item.job : item as Job
        const match = 'overall_score' in item ? item as JobMatch : undefined
        return (
          <JobCard
            key={job.id}
            job={job}
            match={match}
            index={index}
            onView={() => navigate(`/jobs/${job.id}`)}
            onApply={onApply ? () => onApply(job.id) : undefined}
            onSave={onSave ? () => onSave(job.id) : undefined}
          />
        )
      })}

      {/* Pagination */}
      {totalPages > 1 && onPageChange && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center gap-2 pt-4"
        >
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ChevronLeft className="w-4 h-4" />}
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            Prev
          </Button>

          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const page = i + 1
              return (
                <button
                  key={page}
                  onClick={() => onPageChange(page)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-all duration-200 ${
                    currentPage === page
                      ? 'bg-primary-600 text-white'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                  }`}
                >
                  {page}
                </button>
              )
            })}
            {totalPages > 7 && (
              <>
                <span className="text-slate-500 px-1">...</span>
                <button
                  onClick={() => onPageChange(totalPages)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium ${
                    currentPage === totalPages
                      ? 'bg-primary-600 text-white'
                      : 'text-slate-400 hover:bg-white/5'
                  }`}
                >
                  {totalPages}
                </button>
              </>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            rightIcon={<ChevronRight className="w-4 h-4" />}
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            Next
          </Button>
        </motion.div>
      )}
    </div>
  )
}
