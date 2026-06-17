import { useState } from 'react'
import { motion } from 'framer-motion'
import type { SkillCluster } from '@/types'

interface SkillGraphProps {
  skillClusters: SkillCluster[]
}

const CATEGORY_COLORS: Record<string, { fill: string; label: string }> = {
  frontend: { fill: '#6366f1', label: 'Frontend' },
  backend: { fill: '#22c55e', label: 'Backend' },
  cloud: { fill: '#a855f7', label: 'Cloud' },
  data: { fill: '#f97316', label: 'Data' },
  devops: { fill: '#14b8a6', label: 'DevOps' },
  mobile: { fill: '#ec4899', label: 'Mobile' },
  design: { fill: '#eab308', label: 'Design' },
  management: { fill: '#64748b', label: 'Management' },
}

const DEFAULT_COLOR = { fill: '#475569', label: 'Other' }

const proficiencyRadius: Record<string, number> = {
  beginner: 20,
  intermediate: 28,
  advanced: 36,
  expert: 44,
}

interface SkillNode {
  name: string
  category: string
  radius: number
  color: string
  x: number
  y: number
}

function layoutNodes(clusters: SkillCluster[], width: number, height: number): SkillNode[] {
  const nodes: SkillNode[] = []
  const padding = 60

  clusters.forEach((cluster) => {
    const colorInfo = CATEGORY_COLORS[cluster.category.toLowerCase()] ?? DEFAULT_COLOR
    const radius = proficiencyRadius[cluster.proficiency_level] ?? 28

    cluster.skills.forEach((skill) => {
      nodes.push({
        name: skill,
        category: cluster.category.toLowerCase(),
        radius,
        color: colorInfo.fill,
        x: 0,
        y: 0,
      })
    })
  })

  // Simple grid-like random layout with collision avoidance attempt
  const rng = (seed: number) => {
    let s = seed
    return () => {
      s = (s * 9301 + 49297) % 233280
      return s / 233280
    }
  }
  const rand = rng(42)

  nodes.forEach((node) => {
    let placed = false
    let attempts = 0
    while (!placed && attempts < 100) {
      const x = padding + rand() * (width - padding * 2)
      const y = padding + rand() * (height - padding * 2)
      const overlaps = nodes.some(
        (other) =>
          other.x !== 0 &&
          Math.hypot(other.x - x, other.y - y) < other.radius + node.radius + 8
      )
      if (!overlaps) {
        node.x = x
        node.y = y
        placed = true
      }
      attempts++
    }
    if (!placed) {
      node.x = padding + rand() * (width - padding * 2)
      node.y = padding + rand() * (height - padding * 2)
    }
  })

  return nodes
}

export const SkillGraph = ({ skillClusters }: SkillGraphProps) => {
  const [hovered, setHovered] = useState<string | null>(null)

  const width = 600
  const height = 380
  const nodes = layoutNodes(skillClusters, width, height)

  const categories = Array.from(new Set(skillClusters.map((c) => c.category.toLowerCase())))

  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Skill Universe</h3>

      <div className="relative overflow-hidden rounded-xl bg-white/3">
        <svg
          width="100%"
          viewBox={`0 0 ${width} ${height}`}
          className="w-full"
          style={{ height: 380 }}
        >
          {nodes.map((node, i) => {
            const isHov = hovered === node.name
            return (
              <g
                key={`${node.name}-${i}`}
                onMouseEnter={() => setHovered(node.name)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              >
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={isHov ? node.radius + 4 : node.radius}
                  fill={node.color}
                  fillOpacity={isHov ? 0.5 : 0.25}
                  stroke={node.color}
                  strokeWidth={isHov ? 2 : 1}
                  strokeOpacity={isHov ? 1 : 0.6}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: i * 0.03, type: 'spring', stiffness: 300, damping: 20 }}
                />
                {(node.radius >= 28 || isHov) && (
                  <text
                    x={node.x}
                    y={node.y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={isHov ? 11 : node.radius >= 36 ? 10 : 8}
                    fill="white"
                    fillOpacity={0.9}
                    fontWeight={isHov ? '600' : '400'}
                    pointerEvents="none"
                  >
                    {node.name.length > 10 ? node.name.slice(0, 9) + '…' : node.name}
                  </text>
                )}
                {isHov && (
                  <g>
                    <rect
                      x={node.x - 60}
                      y={node.y - node.radius - 36}
                      width={120}
                      height={28}
                      rx={6}
                      fill="#1e1e2e"
                      stroke={node.color}
                      strokeWidth={1}
                      strokeOpacity={0.5}
                    />
                    <text
                      x={node.x}
                      y={node.y - node.radius - 22}
                      textAnchor="middle"
                      fontSize={11}
                      fill="white"
                      fontWeight="600"
                    >
                      {node.name}
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-4">
        {categories.map((cat) => {
          const info = CATEGORY_COLORS[cat] ?? DEFAULT_COLOR
          return (
            <div key={cat} className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: info.fill }}
              />
              <span className="text-xs text-slate-400">{info.label}</span>
            </div>
          )
        })}
        <div className="flex items-center gap-3 ml-auto text-xs text-slate-500">
          <span>Size = Proficiency</span>
        </div>
      </div>
    </div>
  )
}
