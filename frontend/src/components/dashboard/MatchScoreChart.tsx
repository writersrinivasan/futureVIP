import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { MatchScoreDistribution } from '@/types'

interface MatchScoreChartProps {
  data: MatchScoreDistribution[]
}

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dark-card border border-white/10 rounded-xl p-3 shadow-xl">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="text-lg font-bold text-primary-400">{payload[0].value} jobs</p>
      </div>
    )
  }
  return null
}

const getBarColor = (range: string) => {
  const score = parseInt(range)
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#6366f1'
  if (score >= 40) return '#f59e0b'
  return '#f43f5e'
}

export const MatchScoreChart = ({ data }: MatchScoreChartProps) => {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="range"
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getBarColor(entry.range)} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
