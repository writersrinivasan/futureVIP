import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Building2, Calendar, Percent, ChevronDown, Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { applicationsService } from '@/services/applications.service'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { formatDate, formatPercentage, getStatusColor } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { Application, ApplicationStatus } from '@/types'

const COLUMNS: { id: ApplicationStatus; label: string }[] = [
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'screening', label: 'Screening' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer', label: 'Offer' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'rejected', label: 'Rejected' },
]

const NEXT_STATUS: Record<ApplicationStatus, ApplicationStatus[]> = {
  saved: ['applied', 'rejected', 'withdrawn'],
  applied: ['screening', 'rejected', 'withdrawn'],
  screening: ['interview', 'rejected', 'withdrawn'],
  interview: ['offer', 'rejected', 'withdrawn'],
  offer: ['accepted', 'rejected', 'withdrawn'],
  accepted: [],
  rejected: ['applied'],
  withdrawn: ['applied'],
}

function AppCard({
  app,
  onMove,
}: {
  app: Application
  onMove: (id: string, status: ApplicationStatus) => void
}) {
  const [moveOpen, setMoveOpen] = useState(false)
  const nextStatuses = NEXT_STATUS[app.status] ?? []

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="glass-card p-4 space-y-2"
    >
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/30 to-violet-500/20 border border-white/10 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-200 truncate">{app.job?.title ?? 'Unknown Role'}</p>
          <p className="text-xs text-slate-400 truncate">{app.job?.company ?? '—'}</p>
        </div>
        {app.match_score !== undefined && (
          <span className="text-xs font-bold text-indigo-300 bg-indigo-500/15 px-1.5 py-0.5 rounded-full flex-shrink-0">
            {Math.round(app.match_score)}%
          </span>
        )}
      </div>

      {app.applied_at && (
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Calendar className="w-3 h-3" />
          {formatDate(app.applied_at)}
        </div>
      )}

      {app.notes && (
        <p className="text-xs text-slate-500 line-clamp-2 italic">"{app.notes}"</p>
      )}

      {nextStatuses.length > 0 && (
        <div className="relative">
          <button
            onClick={() => setMoveOpen((v) => !v)}
            className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs text-slate-400 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-colors"
          >
            <span>Move to...</span>
            <ChevronDown className={cn('w-3 h-3 transition-transform', moveOpen && 'rotate-180')} />
          </button>
          <AnimatePresence>
            {moveOpen && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute bottom-full mb-1 left-0 right-0 bg-[#1a1a2e] border border-white/15 rounded-lg shadow-xl z-10 py-1"
              >
                {nextStatuses.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      onMove(app.id, s)
                      setMoveOpen(false)
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-slate-300 hover:bg-white/5 transition-colors capitalize"
                  >
                    {s}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  )
}

export default function ApplicationsPage() {
  const queryClient = useQueryClient()

  const { data: appsData, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => applicationsService.getApplications({ per_page: 200 }),
  })

  const { data: stats } = useQuery({
    queryKey: ['application-stats'],
    queryFn: () => applicationsService.getApplicationStats(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ApplicationStatus }) =>
      applicationsService.updateApplication(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      toast.success('Application updated')
    },
    onError: () => toast.error('Failed to update'),
  })

  const apps = appsData?.items ?? []

  const getColumnApps = (status: ApplicationStatus) =>
    apps.filter((a) => a.status === status)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 rounded-xl" />
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((c) => (
            <Skeleton key={c.id} className="w-64 flex-shrink-0 h-96 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 pb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Applications</h1>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total', value: stats.total, icon: <Building2 className="w-4 h-4" /> },
            { label: 'Response Rate', value: formatPercentage(stats.response_rate), icon: <Percent className="w-4 h-4" /> },
            { label: 'Interview Rate', value: formatPercentage(stats.interview_rate), icon: <Calendar className="w-4 h-4" /> },
            { label: 'Offer Rate', value: formatPercentage(stats.offer_rate), icon: <Percent className="w-4 h-4" /> },
          ].map((s) => (
            <div key={s.label} className="glass-card p-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 text-indigo-400 flex items-center justify-center">
                {s.icon}
              </div>
              <div>
                <p className="text-base font-bold text-white">{s.value}</p>
                <p className="text-xs text-slate-400">{s.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Kanban board */}
      <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: '60vh' }}>
        {COLUMNS.map((col) => {
          const colApps = getColumnApps(col.id)
          return (
            <div
              key={col.id}
              className="flex-shrink-0 w-64 flex flex-col rounded-xl border border-white/10 bg-white/3"
            >
              {/* Column header */}
              <div className="flex items-center justify-between p-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <span
                    className={cn('text-xs font-semibold capitalize', getStatusColor(col.id).split(' ')[0])}
                  >
                    {col.label}
                  </span>
                  <span className="text-xs text-slate-500 bg-white/8 px-1.5 py-0.5 rounded-full">
                    {colApps.length}
                  </span>
                </div>
                <button className="text-slate-500 hover:text-slate-300 transition-colors p-0.5 rounded">
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Cards */}
              <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[calc(100vh-280px)]">
                <AnimatePresence>
                  {colApps.length > 0 ? (
                    colApps.map((app) => (
                      <AppCard
                        key={app.id}
                        app={app}
                        onMove={(id, status) => updateMutation.mutate({ id, status })}
                      />
                    ))
                  ) : (
                    <p className="text-xs text-slate-600 text-center py-8">No applications</p>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
