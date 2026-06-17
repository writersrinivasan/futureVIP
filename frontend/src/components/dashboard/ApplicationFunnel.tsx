import { motion } from 'framer-motion'
import type { ApplicationFunnelData } from '@/types'

interface ApplicationFunnelProps {
  data: ApplicationFunnelData[]
}

const stageColors = [
  'from-slate-500 to-slate-600',
  'from-primary-600 to-primary-700',
  'from-accent-500 to-accent-600',
  'from-secondary-500 to-secondary-600',
  'from-success-500 to-success-600',
]

export const ApplicationFunnel = ({ data }: ApplicationFunnelProps) => {
  const maxCount = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="space-y-3">
      {data.map((item, index) => {
        const width = Math.max((item.count / maxCount) * 100, 5)
        return (
          <div key={item.stage} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-20 text-right flex-shrink-0">{item.stage}</span>
            <div className="flex-1 h-7 bg-white/5 rounded-lg overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ duration: 0.8, delay: index * 0.1, ease: 'easeOut' }}
                className={`h-full rounded-lg bg-gradient-to-r ${stageColors[index % stageColors.length]} flex items-center justify-end pr-2`}
              >
                {item.count > 0 && (
                  <span className="text-xs font-bold text-white">{item.count}</span>
                )}
              </motion.div>
            </div>
            {item.conversion_rate !== undefined && (
              <span className="text-xs text-slate-500 w-10 flex-shrink-0">
                {item.conversion_rate.toFixed(0)}%
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
