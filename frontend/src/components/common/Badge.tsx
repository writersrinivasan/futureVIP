import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant =
  | 'default'
  | 'primary'
  | 'secondary'
  | 'accent'
  | 'success'
  | 'warning'
  | 'danger'
  | 'outline'

type BadgeSize = 'sm' | 'md' | 'lg'

interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
  size?: BadgeSize
  className?: string
  dot?: boolean
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-700 text-slate-300 border-slate-600',
  primary: 'bg-primary-500/20 text-primary-300 border-primary-500/30',
  secondary: 'bg-secondary-500/20 text-secondary-300 border-secondary-500/30',
  accent: 'bg-accent-500/20 text-accent-300 border-accent-500/30',
  success: 'bg-success-500/20 text-success-300 border-success-500/30',
  warning: 'bg-warning-500/20 text-warning-300 border-warning-500/30',
  danger: 'bg-danger-500/20 text-danger-300 border-danger-500/30',
  outline: 'bg-transparent text-slate-400 border-slate-600',
}

const dotVariantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-400',
  primary: 'bg-primary-400',
  secondary: 'bg-secondary-400',
  accent: 'bg-accent-400',
  success: 'bg-success-400',
  warning: 'bg-warning-400',
  danger: 'bg-danger-400',
  outline: 'bg-slate-400',
}

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-0.5 text-xs',
  lg: 'px-2.5 py-1 text-sm',
}

export const Badge = ({
  children,
  variant = 'default',
  size = 'md',
  className,
  dot = false,
}: BadgeProps) => {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', dotVariantStyles[variant])}
        />
      )}
      {children}
    </span>
  )
}
