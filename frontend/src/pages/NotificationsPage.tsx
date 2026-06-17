import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Bell, CheckCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { notificationsService } from '@/services/notifications.service'
import { NotificationItem } from '@/components/notifications/NotificationItem'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import type { NotificationType } from '@/types'

type FilterTab = 'all' | NotificationType

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'job_match', label: 'Job Matches' },
  { key: 'application_update', label: 'Applications' },
  { key: 'resume_analyzed', label: 'Resume' },
  { key: 'career_insight', label: 'Career' },
  { key: 'system', label: 'System' },
]

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<FilterTab>('all')

  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications', activeTab],
    queryFn: () =>
      notificationsService.getNotifications(
        activeTab === 'all' ? undefined : { type: activeTab }
      ),
    refetchInterval: 30000,
  })

  const markAllMutation = useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('All notifications marked as read')
    },
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => notificationsService.deleteNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('Notification deleted')
    },
  })

  const notifications = notificationsData?.items ?? []
  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <div className="max-w-3xl mx-auto space-y-4 pb-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Notifications</h1>
          {unreadCount > 0 && (
            <Badge variant="primary" size="sm">{unreadCount} unread</Badge>
          )}
        </div>
        {unreadCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => markAllMutation.mutate()}
            isLoading={markAllMutation.isPending}
            leftIcon={<CheckCheck className="w-4 h-4" />}
          >
            Mark all read
          </Button>
        )}
      </motion.div>

      {/* Filter tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              activeTab === tab.key
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                : 'text-slate-400 hover:text-slate-300 hover:bg-white/5 border border-transparent'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Notifications list */}
      <div className="space-y-2">
        {isLoading ? (
          [...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={<Bell className="w-10 h-10 text-slate-600" />}
            title="No notifications"
            description={
              activeTab === 'all'
                ? "You're all caught up! Notifications will appear here."
                : `No ${activeTab.replace('_', ' ')} notifications.`
            }
          />
        ) : (
          notifications.map((notification, idx) => (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <NotificationItem
                notification={notification}
                onMarkRead={() => markReadMutation.mutate(notification.id)}
                onDelete={() => deleteMutation.mutate(notification.id)}
              />
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
