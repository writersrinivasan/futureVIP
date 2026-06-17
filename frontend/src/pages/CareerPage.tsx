import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { TrendingUp, Wand2, ArrowRight, Target, AlertTriangle, ExternalLink, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import { careerService } from '@/services/career.service'
import { useAuthStore } from '@/store/auth.store'
import { RoadmapTimeline } from '@/components/career/RoadmapTimeline'
import { CareerInsights } from '@/components/career/CareerInsights'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Progress } from '@/components/common/Progress'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import type { CareerRoadmap, SkillGap } from '@/types'

export default function CareerPage() {
  const queryClient = useQueryClient()
  const { user } = useAuthStore()
  const [currentRole, setCurrentRole] = useState(user?.profile?.current_role ?? '')
  const [targetRole, setTargetRole] = useState(user?.profile?.target_role ?? '')
  const [timelineMonths, setTimelineMonths] = useState(12)
  const [showGenerateForm, setShowGenerateForm] = useState(false)

  const { data: roadmap, isLoading: roadmapLoading } = useQuery({
    queryKey: ['career-roadmap'],
    queryFn: () => careerService.getRoadmap(),
  })

  const { data: insightsData, isLoading: insightsLoading } = useQuery({
    queryKey: ['career-insights'],
    queryFn: () => careerService.getCareerInsights(),
  })

  const { data: skillsData } = useQuery({
    queryKey: ['user-skills'],
    queryFn: () => careerService.getSkills(),
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      careerService.generateRoadmap({ current_role: currentRole, target_role: targetRole, timeline_months: timelineMonths }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['career-roadmap'] })
      setShowGenerateForm(false)
      toast.success('Career roadmap generated!')
    },
    onError: () => toast.error('Failed to generate roadmap. Please try again.'),
  })

  const skills = skillsData?.skills ?? []
  const proficiency = skillsData?.proficiency ?? {}
  const insights = insightsData ?? []

  // Derive progress from milestones since CareerRoadmap has no progress field
  const progress = roadmap && roadmap.milestones.length > 0
    ? Math.round((roadmap.milestones.filter((m) => m.is_completed).length / roadmap.milestones.length) * 100)
    : 0

  return (
    <div className="space-y-6 pb-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-white">Career Roadmap</h1>
          <p className="text-sm text-slate-400 mt-0.5">AI-powered plan to reach your target role</p>
        </div>
        <Button
          variant="primary"
          onClick={() => setShowGenerateForm(!showGenerateForm)}
          leftIcon={<Wand2 className="w-4 h-4" />}
        >
          {roadmap ? 'Regenerate' : 'Generate Roadmap'}
        </Button>
      </motion.div>

      {/* Generate form */}
      {showGenerateForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="glass-card p-5 space-y-4"
        >
          <h3 className="text-base font-semibold text-white">Define Your Career Path</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Current Role</label>
              <input
                value={currentRole}
                onChange={(e) => setCurrentRole(e.target.value)}
                placeholder="e.g. Software Engineer"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Role</label>
              <input
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Staff Engineer"
                className="input-field text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Timeline: <span className="text-indigo-400">{timelineMonths} months</span>
            </label>
            <input
              type="range"
              min={3}
              max={36}
              step={3}
              value={timelineMonths}
              onChange={(e) => setTimelineMonths(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>3 months</span><span>36 months</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => generateMutation.mutate()}
              isLoading={generateMutation.isPending}
              disabled={!currentRole.trim() || !targetRole.trim()}
            >
              Generate
            </Button>
            <Button variant="ghost" onClick={() => setShowGenerateForm(false)}>Cancel</Button>
          </div>
        </motion.div>
      )}

      {roadmapLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      ) : !roadmap ? (
        <EmptyState
          icon={<TrendingUp className="w-10 h-10 text-indigo-400" />}
          title="No roadmap yet"
          description="Generate a personalized career roadmap to see your path to your target role."
          action={{ label: 'Generate Roadmap', onClick: () => setShowGenerateForm(true) }}
        />
      ) : (
        <>
          {/* Role banner */}
          <Card className="p-5">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex items-center gap-3 flex-1">
                <div className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-slate-300">
                  {roadmap.current_role || 'Current Role'}
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-sm font-medium text-indigo-300">
                  <Target className="w-3.5 h-3.5" />
                  {roadmap.target_role || 'Target Role'}
                </div>
              </div>
              <div className="flex items-center gap-3 sm:text-right">
                <div>
                  <p className="text-xs text-slate-500">Progress</p>
                  <p className="text-base font-bold text-white">{progress}%</p>
                </div>
                <div className="w-20">
                  <Progress value={progress} variant="primary" size="sm" />
                </div>
              </div>
            </div>
          </Card>

          {/* Roadmap timeline */}
          <RoadmapTimeline milestones={roadmap.milestones} />

          {/* Two-column: Skills + CareerInsights */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h2 className="text-base font-semibold text-white mb-3">Your Skills</h2>
              {skills.length > 0 ? (
                <Card className="p-4 space-y-2">
                  {skills.slice(0, 10).map((skill) => (
                    <div key={skill} className="flex items-center justify-between gap-2">
                      <span className="text-sm text-slate-300 truncate">{skill}</span>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            className={`w-3 h-3 ${(proficiency[skill] ?? 0) >= star * 2 ? 'text-amber-400 fill-amber-400' : 'text-slate-700'}`}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </Card>
              ) : (
                <Card className="p-6 flex items-center justify-center h-48">
                  <p className="text-sm text-slate-500">Upload a resume to see your skills</p>
                </Card>
              )}
            </div>
            <div>
              <h2 className="text-base font-semibold text-white mb-3">Career Insights</h2>
              {insightsLoading ? (
                <Skeleton className="h-48 rounded-xl" />
              ) : insights.length > 0 ? (
                <CareerInsights insights={insights} />
              ) : (
                <Card className="p-6 flex items-center justify-center h-48">
                  <p className="text-sm text-slate-500">No insights available yet</p>
                </Card>
              )}
            </div>
          </div>

          {/* Skill gaps */}
          {roadmap.skill_gaps?.length > 0 && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Skill Gaps to Address
              </h2>
              <div className="space-y-3">
                {roadmap.skill_gaps.slice(0, 6).map((gap, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-4 p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-3 min-w-0">
                      <Badge variant={gap.priority === 'high' ? 'danger' : gap.priority === 'medium' ? 'warning' : 'default'} size="sm">
                        {gap.priority}
                      </Badge>
                      <span className="text-sm font-medium text-slate-200 truncate">{gap.skill}</span>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <div className="text-xs text-slate-500 hidden sm:block">
                        {gap.current_level}/10 → {gap.required_level}/10
                      </div>
                      {gap.resources?.[0] && (
                        <a
                          href={gap.resources[0].url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
