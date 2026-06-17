import { motion } from 'framer-motion'
import { Briefcase, FileText, Star, MessageSquare, Trophy } from 'lucide-react'
import { formatTimeAgo } from '@/utils/format'
import type { ActivityItem } from '@/types'

interface ActivityTimelineProps {
  activities: ActivityItem[]
}

const activityConfig = {
  application: {
    icon: Briefcase,
    color: 'bg-primary-500/20 text-primary-400',
  },
  match: {
    icon: Star,
    color: 'bg-accent-500/20 text-accent-400',
  },
  resume_update: {
    icon: FileText,
    color: 'bg-secondary-500/20 text-secondary-400',
  },
  interview: {
    icon: MessageSquare,
    color: 'bg-warning-500/20 text-warning-400',
  },
  offer: {
    icon: Trophy,
    color: 'bg-success-500/20 text-success-400',
  },
}

export const ActivityTimeline = ({ activities }: ActivityTimelineProps) => {
  if (!activities.length) {
    return (
      <div className="text-center py-8 text-slate-500 text-sm">
        No recent activity
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {activities.map((activity, index) => {
        const config = activityConfig[activity.type] || activityConfig.application
        const Icon = config.icon

        return (
          <motion.div
            key={activity.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className="flex gap-3"
          >
            {/* Timeline line */}
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${config.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              {index < activities.length - 1 && (
                <div className="w-px flex-1 bg-white/10 mt-1 min-h-4" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 pb-4">
              <p className="text-sm font-medium text-slate-200">{activity.title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{activity.description}</p>
              <p className="text-xs text-slate-600 mt-1">{formatTimeAgo(activity.timestamp)}</p>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
