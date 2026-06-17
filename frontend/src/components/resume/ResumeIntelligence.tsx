import { motion } from 'framer-motion'
import {
  TrendingUp,
  Award,
  Clock,
  Target,
  Layers,
  AlertTriangle,
  CheckCircle,
  Briefcase,
} from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import type { ResumeAnalysis } from '@/types'

interface ResumeIntelligenceProps {
  analysis: ResumeAnalysis
}

export const ResumeIntelligence = ({ analysis }: ResumeIntelligenceProps) => {
  const proficiencyColors = {
    beginner: 'primary',
    intermediate: 'accent',
    advanced: 'secondary',
    expert: 'success',
  } as const

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            icon: Award,
            label: 'Seniority',
            value: analysis.seniority_level,
            color: 'text-primary-400 bg-primary-500/20',
          },
          {
            icon: Clock,
            label: 'Experience',
            value: `${analysis.years_experience} yrs`,
            color: 'text-accent-400 bg-accent-500/20',
          },
          {
            icon: TrendingUp,
            label: 'Trajectory',
            value: analysis.career_trajectory,
            color: 'text-success-400 bg-success-500/20',
          },
          {
            icon: Briefcase,
            label: 'Suggested Roles',
            value: `${analysis.suggested_roles.length} roles`,
            color: 'text-secondary-400 bg-secondary-500/20',
          },
        ].map((metric, index) => {
          const Icon = metric.icon
          return (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white/5 rounded-xl p-4"
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${metric.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <p className="text-xs text-slate-400 mb-0.5">{metric.label}</p>
              <p className="text-sm font-semibold text-slate-200 capitalize">{metric.value}</p>
            </motion.div>
          )
        })}
      </div>

      {/* Value Proposition */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-primary-400" />
          <h4 className="text-sm font-semibold text-slate-200">Value Proposition</h4>
        </div>
        <p className="text-sm text-slate-400 bg-white/3 rounded-xl p-4 leading-relaxed">
          {analysis.value_proposition}
        </p>
      </div>

      {/* Skill Clusters */}
      {analysis.skill_clusters.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-accent-400" />
            <h4 className="text-sm font-semibold text-slate-200">Skill Clusters</h4>
          </div>
          <div className="space-y-3">
            {analysis.skill_clusters.map((cluster, index) => (
              <motion.div
                key={cluster.category}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white/3 rounded-xl p-4"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-slate-300">{cluster.category}</span>
                  <Badge
                    variant={proficiencyColors[cluster.proficiency_level]}
                    size="sm"
                  >
                    {cluster.proficiency_level}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {cluster.skills.map((skill) => (
                    <Badge key={skill} variant="outline" size="sm">{skill}</Badge>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Achievements */}
      {analysis.achievements.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-success-400" />
            <h4 className="text-sm font-semibold text-slate-200">Key Achievements</h4>
          </div>
          <div className="space-y-2">
            {analysis.achievements.map((achievement, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex gap-2.5 p-3 bg-success-500/5 border border-success-500/20 rounded-xl"
              >
                <CheckCircle className="w-4 h-4 text-success-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-slate-300">{achievement}</p>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Red Flags */}
      {analysis.red_flags.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-danger-400" />
            <h4 className="text-sm font-semibold text-slate-200">Areas of Concern</h4>
          </div>
          <div className="space-y-2">
            {analysis.red_flags.map((flag, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex gap-2.5 p-3 bg-danger-500/5 border border-danger-500/20 rounded-xl"
              >
                <AlertTriangle className="w-4 h-4 text-danger-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-slate-300">{flag}</p>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Roles */}
      {analysis.suggested_roles.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-secondary-400" />
            <h4 className="text-sm font-semibold text-slate-200">Suggested Target Roles</h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {analysis.suggested_roles.map((role) => (
              <Badge key={role} variant="secondary" size="md">{role}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
