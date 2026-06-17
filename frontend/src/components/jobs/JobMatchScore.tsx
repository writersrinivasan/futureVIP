import { motion } from 'framer-motion'
import { Target, Code, Briefcase, MapPin, TrendingUp } from 'lucide-react'
import { Progress } from '@/components/common/Progress'
import type { JobMatch } from '@/types'

interface JobMatchScoreProps {
  match: JobMatch
}

export const JobMatchScore = ({ match }: JobMatchScoreProps) => {
  const breakdowns: Array<{
    icon: typeof Target
    label: string
    value: number
    color: 'primary' | 'success' | 'warning' | 'danger' | 'gradient'
  }> = [
    { icon: Target,    label: 'Overall Match',   value: match.overall_score,               color: 'primary'  },
    { icon: TrendingUp,label: 'Semantic Match',   value: match.embedding_similarity * 100,  color: 'gradient' },
    { icon: Code,      label: 'Skill Overlap',    value: match.skill_overlap * 100,         color: 'success'  },
    { icon: Briefcase, label: 'Experience Fit',   value: match.experience_alignment * 100,  color: 'warning'  },
    { icon: MapPin,    label: 'Location Match',   value: match.location_match * 100,        color: 'primary'  },
  ]

  return (
    <div className="space-y-4">
      {/* Overall score circle */}
      <div className="flex items-center gap-4 p-4 bg-white/3 rounded-xl">
        <div className="relative">
          <svg viewBox="0 0 36 36" className="w-16 h-16">
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="3"
            />
            <motion.path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#6366f1"
              strokeWidth="3"
              strokeDasharray={`${match.overall_score}, 100`}
              strokeDashoffset="25"
              strokeLinecap="round"
              initial={{ strokeDasharray: '0, 100' }}
              animate={{ strokeDasharray: `${match.overall_score}, 100` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-primary-300">
              {Math.round(match.overall_score)}%
            </span>
          </div>
        </div>
        <div>
          <p className="text-base font-bold text-slate-200">
            {match.overall_score >= 85
              ? 'Excellent Match'
              : match.overall_score >= 70
              ? 'Great Match'
              : match.overall_score >= 55
              ? 'Good Match'
              : 'Partial Match'}
          </p>
          <p className="text-xs text-slate-400">
            {match.matched_skills.length} of {match.matched_skills.length + match.missing_skills.length} skills matched
          </p>
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-3">
        {breakdowns.map((item, index) => {
          const Icon = item.icon
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.07 }}
              className="flex items-center gap-3"
            >
              <Icon className="w-4 h-4 text-slate-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-slate-400">{item.label}</span>
                  <span className="text-xs font-semibold text-slate-300">
                    {Math.round(item.value)}%
                  </span>
                </div>
                <Progress value={item.value} size="sm" variant={item.color} animated={false} />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
