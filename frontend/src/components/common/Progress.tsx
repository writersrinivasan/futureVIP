import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'

interface ProgressProps {
  value: number
  max?: number
  label?: string
  showPercentage?: boolean
  size?: 'sm' | 'md' | 'lg'
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'gradient'
  animated?: boolean
  className?: string
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

const variantStyles = {
  primary: 'bg-primary-500',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  gradient: 'bg-gradient-to-r from-primary-500 via-secondary-500 to-accent-500',
}

export const Progress = ({
  value,
  max = 100,
  label,
  showPercentage = false,
  size = 'md',
  variant = 'primary',
  animated = true,
  className,
}: ProgressProps) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const getAutoVariant = (): keyof typeof variantStyles => {
    if (variant !== 'primary') return variant
    if (percentage >= 80) return 'success'
    if (percentage >= 60) return 'warning'
    if (percentage < 40) return 'danger'
    return 'primary'
  }

  return (
    <div className={cn('w-full', className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && <span className="text-sm text-slate-400">{label}</span>}
          {showPercentage && (
            <span className="text-sm font-semibold text-slate-300">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div
        className={cn(
          'w-full bg-white/10 rounded-full overflow-hidden',
          sizeStyles[size]
        )}
      >
        {animated ? (
          <motion.div
            className={cn('h-full rounded-full', variantStyles[getAutoVariant()])}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        ) : (
          <div
            className={cn('h-full rounded-full', variantStyles[getAutoVariant()])}
            style={{ width: `${percentage}%` }}
          />
        )}
      </div>
    </div>
  )
}
