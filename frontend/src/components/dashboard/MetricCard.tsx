import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'

interface MetricCardProps {
  icon: ReactNode
  value: string | number
  label: string
  trend?: {
    value: number
    label?: string
  }
  color?: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'danger'
  suffix?: string
  index?: number
  onClick?: () => void
}

const colorStyles = {
  primary: {
    icon: 'bg-primary-500/20 text-primary-400',
    value: 'text-primary-300',
    glow: 'shadow-primary-500/10',
  },
  secondary: {
    icon: 'bg-secondary-500/20 text-secondary-400',
    value: 'text-secondary-300',
    glow: 'shadow-secondary-500/10',
  },
  accent: {
    icon: 'bg-accent-500/20 text-accent-400',
    value: 'text-accent-300',
    glow: 'shadow-accent-500/10',
  },
  success: {
    icon: 'bg-success-500/20 text-success-400',
    value: 'text-success-300',
    glow: 'shadow-success-500/10',
  },
  warning: {
    icon: 'bg-warning-500/20 text-warning-400',
    value: 'text-warning-300',
    glow: 'shadow-warning-500/10',
  },
  danger: {
    icon: 'bg-danger-500/20 text-danger-400',
    value: 'text-danger-300',
    glow: 'shadow-danger-500/10',
  },
}

export const MetricCard = ({
  icon,
  value,
  label,
  trend,
  color = 'primary',
  suffix,
  index = 0,
  onClick,
}: MetricCardProps) => {
  const styles = colorStyles[color]
  const trendUp = trend && trend.value > 0
  const trendDown = trend && trend.value < 0
  const trendNeutral = trend && trend.value === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      whileHover={{ scale: 1.02, y: -2 }}
      className={cn(
        'glass-card p-5 cursor-pointer',
        'hover:bg-white/8 hover:border-white/20 transition-all duration-300',
        `shadow-lg ${styles.glow}`
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', styles.icon)}>
          {icon}
        </div>
        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full',
              trendUp ? 'bg-success-500/10 text-success-400' : '',
              trendDown ? 'bg-danger-500/10 text-danger-400' : '',
              trendNeutral ? 'bg-slate-500/10 text-slate-400' : ''
            )}
          >
            {trendUp && <TrendingUp className="w-3 h-3" />}
            {trendDown && <TrendingDown className="w-3 h-3" />}
            {trendNeutral && <Minus className="w-3 h-3" />}
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: index * 0.05 + 0.2 }}
      >
        <div className="flex items-baseline gap-1 mb-1">
          <span className={cn('text-2xl font-bold', styles.value)}>
            {value}
          </span>
          {suffix && <span className="text-sm text-slate-500">{suffix}</span>}
        </div>
        <p className="text-sm text-slate-400 font-medium">{label}</p>
        {trend?.label && (
          <p className="text-xs text-slate-500 mt-1">{trend.label}</p>
        )}
      </motion.div>
    </motion.div>
  )
}
