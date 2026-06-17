import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Briefcase, FileText, Bell, File, Trash2 } from 'lucide-react'
import { formatTimeAgo } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { Notification } from '@/types'

interface NotificationItemProps {
  notification: Notification
  onMarkRead: (id: string) => void
  onDelete: (id: string) => void
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  job_match: <Briefcase className="w-4 h-4" />,
  application_update: <FileText className="w-4 h-4" />,
  resume_analyzed: <File className="w-4 h-4" />,
  interview_reminder: <Bell className="w-4 h-4" />,
  career_insight: <Bell className="w-4 h-4" />,
  system: <Bell className="w-4 h-4" />,
}

const TYPE_COLORS: Record<string, string> = {
  job_match: 'bg-indigo-500/20 text-indigo-400',
  application_update: 'bg-green-500/20 text-green-400',
  resume_analyzed: 'bg-violet-500/20 text-violet-400',
  interview_reminder: 'bg-amber-500/20 text-amber-400',
  career_insight: 'bg-cyan-500/20 text-cyan-400',
  system: 'bg-slate-500/20 text-slate-400',
}

export const NotificationItem = ({ notification, onMarkRead, onDelete }: NotificationItemProps) => {
  const [showDelete, setShowDelete] = useState(false)

  const handleClick = () => {
    if (!notification.is_read) {
      onMarkRead(notification.id)
    }
  }

  const icon = TYPE_ICONS[notification.type] ?? TYPE_ICONS.system
  const iconColor = TYPE_COLORS[notification.type] ?? TYPE_COLORS.system

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={cn(
        'relative flex items-start gap-3 p-4 rounded-xl border transition-all duration-200 cursor-pointer group',
        notification.is_read
          ? 'bg-white/3 border-white/8 hover:bg-white/5'
          : 'bg-indigo-500/8 border-indigo-500/20 hover:bg-indigo-500/12'
      )}
      onClick={handleClick}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      {/* Unread dot */}
      {!notification.is_read && (
        <div className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-indigo-400" />
      )}

      {/* Icon */}
      <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5', iconColor)}>
        {icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={cn('text-sm font-semibold mb-0.5', notification.is_read ? 'text-slate-300' : 'text-slate-100')}>
          {notification.title}
        </p>
        <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
          {notification.message}
        </p>
        <p className="text-xs text-slate-600 mt-1.5">{formatTimeAgo(notification.created_at)}</p>
      </div>

      {/* Delete button on hover */}
      <AnimatePresence>
        {showDelete && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={(e) => {
              e.stopPropagation()
              onDelete(notification.id)
            }}
            className="flex-shrink-0 p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
