import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'

interface ATSGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export const ATSGauge = ({ score, size = 'md', showLabel = true, className }: ATSGaugeProps) => {
  const clampedScore = Math.min(Math.max(score, 0), 100)
  const radius = size === 'lg' ? 54 : size === 'sm' ? 36 : 46
  const strokeWidth = size === 'lg' ? 8 : size === 'sm' ? 5 : 6
  const circumference = 2 * Math.PI * radius
  const svgSize = (radius + strokeWidth) * 2

  // Only use 75% of the circle (270 degrees)
  const arcLength = circumference * 0.75
  const strokeDashoffset = arcLength - (clampedScore / 100) * arcLength

  const getColor = () => {
    if (clampedScore >= 80) return '#22c55e' // success
    if (clampedScore >= 60) return '#f59e0b' // warning
    return '#f43f5e' // danger
  }

  const getLabel = () => {
    if (clampedScore >= 80) return 'Excellent'
    if (clampedScore >= 60) return 'Good'
    if (clampedScore >= 40) return 'Fair'
    return 'Poor'
  }

  const color = getColor()
  const rotation = -225 // Start at bottom-left (225 deg from top)

  const textSize = size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-lg' : 'text-2xl'
  const labelSize = size === 'sm' ? 'text-xs' : 'text-sm'

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <div className="relative">
        <svg
          width={svgSize}
          height={svgSize}
          viewBox={`0 0 ${svgSize} ${svgSize}`}
          className="overflow-visible"
        >
          {/* Background track */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            transform={`rotate(${rotation} ${svgSize / 2} ${svgSize / 2})`}
            strokeLinecap="round"
          />
          {/* Score arc */}
          <motion.circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={arcLength}
            transform={`rotate(${rotation} ${svgSize / 2} ${svgSize / 2})`}
            strokeLinecap="round"
            animate={{ strokeDashoffset }}
            initial={{ strokeDashoffset: arcLength }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
            style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.5 }}
            className={cn('font-bold leading-none', textSize)}
            style={{ color }}
          >
            {Math.round(clampedScore)}
          </motion.span>
          <span className="text-xs text-slate-500 mt-0.5">/100</span>
        </div>
      </div>

      {showLabel && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-center mt-1"
        >
          <p className={cn('font-semibold', labelSize)} style={{ color }}>
            {getLabel()}
          </p>
          <p className="text-xs text-slate-500">ATS Score</p>
        </motion.div>
      )}
    </div>
  )
}
