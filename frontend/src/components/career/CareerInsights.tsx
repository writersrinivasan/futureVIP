import { motion } from 'framer-motion'
import { TrendingUp, DollarSign, Star, Users } from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import { Progress } from '@/components/common/Progress'
import { EmptyState } from '@/components/common/EmptyState'
import type { CareerInsight } from '@/types'

interface CareerInsightsProps {
  insights: CareerInsight[]
}

const TYPE_CONFIG: Record<
  string,
  { icon: React.ReactNode; label: string; variant: 'primary' | 'success' | 'warning' | 'accent' }
> = {
  market_trend: {
    icon: <TrendingUp className="w-5 h-5" />,
    label: 'Market Trend',
    variant: 'primary',
  },
  salary_data: {
    icon: <DollarSign className="w-5 h-5" />,
    label: 'Salary Data',
    variant: 'success',
  },
  opportunity: {
    icon: <Star className="w-5 h-5" />,
    label: 'Opportunity',
    variant: 'warning',
  },
  competition: {
    icon: <Users className="w-5 h-5" />,
    label: 'Competition',
    variant: 'accent',
  },
}

const iconBgColors: Record<string, string> = {
  market_trend: 'bg-indigo-500/20 text-indigo-400',
  salary_data: 'bg-green-500/20 text-green-400',
  opportunity: 'bg-amber-500/20 text-amber-400',
  competition: 'bg-cyan-500/20 text-cyan-400',
}

export const CareerInsights = ({ insights }: CareerInsightsProps) => {
  if (insights.length === 0) {
    return (
      <EmptyState
        icon={<TrendingUp className="w-6 h-6" />}
        title="No insights yet"
        description="Generate a career roadmap to unlock market insights."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {insights.map((insight, i) => {
        const config = TYPE_CONFIG[insight.type] ?? TYPE_CONFIG.market_trend
        const bgColor = iconBgColors[insight.type] ?? 'bg-slate-500/20 text-slate-400'

        return (
          <motion.div
            key={insight.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="glass-card p-5 flex flex-col gap-3"
          >
            {/* Header */}
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${bgColor}`}>
                {config.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={config.variant} size="sm">
                    {config.label}
                  </Badge>
                </div>
                <h4 className="text-sm font-semibold text-slate-200 leading-snug">{insight.title}</h4>
              </div>
            </div>

            {/* Description */}
            <p className="text-xs text-slate-400 leading-relaxed flex-1">{insight.description}</p>

            {/* Relevance */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-500">Relevance</span>
                <span className="text-slate-300 font-medium">
                  {Math.round(insight.relevance_score * 100)}%
                </span>
              </div>
              <Progress
                value={insight.relevance_score * 100}
                size="sm"
                variant={
                  insight.relevance_score >= 0.8
                    ? 'success'
                    : insight.relevance_score >= 0.6
                    ? 'primary'
                    : 'warning'
                }
                animated
              />
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
