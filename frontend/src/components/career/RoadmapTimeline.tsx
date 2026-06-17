import { motion } from 'framer-motion'
import { CheckCircle, Circle, Clock, BookOpen, ExternalLink } from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { formatDate } from '@/utils/format'
import type { RoadmapMilestone } from '@/types'

interface RoadmapTimelineProps {
  milestones: RoadmapMilestone[]
  onToggleComplete?: (milestoneId: string, completed: boolean) => void
}

const resourceTypeIcons = {
  course: '🎓',
  book: '📚',
  article: '📄',
  video: '🎬',
  project: '💻',
  certification: '🏆',
}

export const RoadmapTimeline = ({ milestones, onToggleComplete }: RoadmapTimelineProps) => {
  const sorted = [...milestones].sort((a, b) => a.timeline_days - b.timeline_days)

  const getTimeLabel = (days: number) => {
    if (days <= 30) return '30 days'
    if (days <= 60) return '60 days'
    if (days <= 90) return '90 days'
    return `${days} days`
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-5 top-0 bottom-0 w-px bg-white/10" />

      <div className="space-y-6">
        {sorted.map((milestone, index) => (
          <motion.div
            key={milestone.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            className="flex gap-4"
          >
            {/* Timeline dot */}
            <div className="relative z-10 flex-shrink-0">
              <button
                onClick={() => onToggleComplete?.(milestone.id, !milestone.is_completed)}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 bg-dark-bg border-2"
                style={{
                  borderColor: milestone.is_completed ? '#22c55e' : 'rgba(255,255,255,0.15)',
                }}
              >
                {milestone.is_completed ? (
                  <CheckCircle className="w-5 h-5 text-success-400" />
                ) : (
                  <Circle className="w-5 h-5 text-slate-500" />
                )}
              </button>
            </div>

            {/* Content */}
            <div
              className={`flex-1 pb-2 rounded-xl p-4 border transition-all duration-300 ${
                milestone.is_completed
                  ? 'bg-success-500/5 border-success-500/20'
                  : 'glass-card'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h4 className={`text-sm font-semibold ${
                    milestone.is_completed ? 'text-success-300 line-through' : 'text-slate-200'
                  }`}>
                    {milestone.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={milestone.is_completed ? 'success' : 'default'} size="sm" dot>
                      {getTimeLabel(milestone.timeline_days)}
                    </Badge>
                    {milestone.completed_at && (
                      <span className="text-xs text-slate-500">
                        Completed {formatDate(milestone.completed_at)}
                      </span>
                    )}
                  </div>
                </div>
                <Clock className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
              </div>

              <p className="text-xs text-slate-400 mb-3">{milestone.description}</p>

              {/* Skills */}
              {milestone.skills_to_learn.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-slate-500 mb-1.5">Skills to learn:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {milestone.skills_to_learn.map((skill) => (
                      <Badge key={skill} variant="primary" size="sm">{skill}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Resources */}
              {milestone.resources.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1.5 flex items-center gap-1">
                    <BookOpen className="w-3 h-3" /> Resources:
                  </p>
                  <div className="space-y-1.5">
                    {milestone.resources.slice(0, 3).map((resource, i) => (
                      <a
                        key={i}
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-xs text-primary-400 hover:text-primary-300 transition-colors group"
                      >
                        <span>{resourceTypeIcons[resource.type] || '🔗'}</span>
                        <span className="flex-1 truncate">{resource.title}</span>
                        {resource.is_free && (
                          <Badge variant="success" size="sm">Free</Badge>
                        )}
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
