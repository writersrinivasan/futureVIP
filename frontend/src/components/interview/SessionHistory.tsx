import { motion } from 'framer-motion'
import { Calendar, MessageSquare, PlayCircle, BarChart2 } from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { EmptyState } from '@/components/common/EmptyState'
import { formatDate } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { InterviewSession } from '@/types'

interface SessionHistoryProps {
  sessions: InterviewSession[]
  activeSessionId?: string
  onSelect: (session: InterviewSession) => void
}

const statusVariant: Record<string, 'success' | 'warning' | 'primary'> = {
  completed: 'success',
  paused: 'warning',
  active: 'primary',
}

const getScoreColor = (score?: number) => {
  if (!score) return 'text-slate-500'
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-amber-400'
  return 'text-red-400'
}

export const SessionHistory = ({ sessions, activeSessionId, onSelect }: SessionHistoryProps) => {
  if (sessions.length === 0) {
    return (
      <EmptyState
        icon={<MessageSquare className="w-6 h-6" />}
        title="No sessions yet"
        description="Start your first mock interview to begin practicing."
      />
    )
  }

  return (
    <div className="space-y-2">
      {sessions.map((session, index) => {
        const isActive = session.id === activeSessionId

        return (
          <motion.div
            key={session.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onSelect(session)}
            className={cn(
              'p-4 rounded-xl border cursor-pointer transition-all duration-200',
              isActive
                ? 'bg-indigo-500/15 border-indigo-500/40'
                : 'bg-white/5 border-white/10 hover:bg-white/8 hover:border-white/20'
            )}
          >
            {/* Title row */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-200 truncate">
                  {session.job_title ?? session.session_type.charAt(0).toUpperCase() + session.session_type.slice(1) + ' Interview'}
                </p>
                {session.company && (
                  <p className="text-xs text-slate-400 truncate">{session.company}</p>
                )}
              </div>
              <Badge variant={statusVariant[session.status] ?? 'default'} size="sm">
                {session.status}
              </Badge>
            </div>

            {/* Meta */}
            <div className="flex items-center gap-3 text-xs text-slate-500 mb-3">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDate(session.started_at)}
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3" />
                {session.answered_questions}/{session.total_questions} Qs
              </span>
            </div>

            {/* Score + action */}
            <div className="flex items-center justify-between">
              {session.overall_score !== undefined ? (
                <div className="flex items-center gap-1.5">
                  <BarChart2 className="w-3.5 h-3.5 text-slate-500" />
                  <span className={cn('text-sm font-bold', getScoreColor(session.overall_score))}>
                    {Math.round(session.overall_score)}/100
                  </span>
                </div>
              ) : (
                <span className="text-xs text-slate-500">No score yet</span>
              )}

              <Button
                variant={isActive ? 'primary' : 'ghost'}
                size="sm"
                leftIcon={<PlayCircle className="w-3.5 h-3.5" />}
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect(session)
                }}
              >
                {session.status === 'completed' ? 'View Results' : 'Resume'}
              </Button>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
