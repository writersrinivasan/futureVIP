import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts'
import type { SkillGapRadarData } from '@/types'

interface SkillGapRadarProps {
  data: SkillGapRadarData[]
}

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dark-card border border-white/10 rounded-xl p-3 shadow-xl">
        <p className="text-sm font-semibold text-slate-200 mb-2">{label}</p>
        {payload.map((p) => (
          <div key={p.name} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="text-slate-400">{p.name}:</span>
            <span className="text-slate-200 font-medium">{p.value}/10</span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export const SkillGapRadar = ({ data }: SkillGapRadarProps) => {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="skill"
          tick={{ fill: '#64748b', fontSize: 10 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Radar
          name="Required"
          dataKey="required"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.15}
          strokeWidth={1.5}
        />
        <Radar
          name="Current"
          dataKey="current"
          stroke="#22d3ee"
          fill="#22d3ee"
          fillOpacity={0.2}
          strokeWidth={2}
        />
        <Legend
          formatter={(value) => (
            <span className="text-xs text-slate-400">{value}</span>
          )}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
