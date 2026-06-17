import { cn } from '@/utils/cn'

interface SkeletonProps {
  className?: string
}

export const Skeleton = ({ className }: SkeletonProps) => {
  return (
    <div
      className={cn(
        'animate-pulse bg-white/5 rounded-lg',
        className
      )}
    />
  )
}

export const CardSkeleton = () => (
  <div className="glass-card p-5 space-y-4">
    <div className="flex items-center gap-3">
      <Skeleton className="w-10 h-10 rounded-lg" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
    <Skeleton className="h-3 w-full" />
    <Skeleton className="h-3 w-4/5" />
    <Skeleton className="h-3 w-2/3" />
  </div>
)

export const MetricCardSkeleton = () => (
  <div className="glass-card p-5 space-y-3">
    <div className="flex justify-between items-start">
      <Skeleton className="w-8 h-8 rounded-lg" />
      <Skeleton className="w-12 h-5 rounded-full" />
    </div>
    <Skeleton className="h-8 w-20" />
    <Skeleton className="h-3 w-24" />
  </div>
)

export const JobCardSkeleton = () => (
  <div className="glass-card p-5 space-y-4">
    <div className="flex gap-3">
      <Skeleton className="w-12 h-12 rounded-xl flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-2/5" />
      </div>
      <Skeleton className="w-14 h-8 rounded-full" />
    </div>
    <div className="flex gap-2">
      <Skeleton className="h-6 w-16 rounded-full" />
      <Skeleton className="h-6 w-20 rounded-full" />
      <Skeleton className="h-6 w-14 rounded-full" />
    </div>
    <Skeleton className="h-2 w-full rounded-full" />
    <div className="flex justify-between">
      <Skeleton className="h-9 w-24 rounded-lg" />
      <Skeleton className="h-9 w-20 rounded-lg" />
    </div>
  </div>
)

export const TableRowSkeleton = ({ cols = 5 }: { cols?: number }) => (
  <tr className="border-b border-white/5">
    {Array.from({ length: cols }).map((_, i) => (
      <td key={i} className="px-4 py-3">
        <Skeleton className="h-4 w-full" />
      </td>
    ))}
  </tr>
)

export const NotificationSkeleton = () => (
  <div className="flex gap-3 p-4 border-b border-white/5">
    <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  </div>
)
