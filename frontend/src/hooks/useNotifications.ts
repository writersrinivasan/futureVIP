import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { notificationsService } from '@/services/notifications.service'
import { useUIStore } from '@/store/ui.store'

const POLLING_INTERVAL = 60 * 1000 // 60 seconds

export const useNotifications = () => {
  const queryClient = useQueryClient()
  const setUnreadCount = useUIStore((s) => s.setUnreadNotificationsCount)

  // Fetch unread count for polling
  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsService.getUnreadCount(),
    refetchInterval: POLLING_INTERVAL,
    staleTime: 30 * 1000,
  })

  // Update global store when count changes
  useEffect(() => {
    if (unreadData?.count !== undefined) {
      setUnreadCount(unreadData.count)
    }
  }, [unreadData?.count, setUnreadCount])

  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsService.getNotifications({ per_page: 50 }),
    staleTime: 30 * 1000,
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] })
      setUnreadCount(0)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => notificationsService.deleteNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })

  return {
    notifications: notificationsData?.items || [],
    total: notificationsData?.total || 0,
    unreadCount: unreadData?.count || 0,
    isLoading,
    markRead: markReadMutation.mutate,
    markAllRead: markAllReadMutation.mutate,
    deleteNotification: deleteMutation.mutate,
    isMarkingRead: markReadMutation.isPending,
    isMarkingAllRead: markAllReadMutation.isPending,
  }
}
