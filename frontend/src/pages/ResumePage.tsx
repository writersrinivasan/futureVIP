import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import * as Tabs from '@radix-ui/react-tabs'
import { FileText, Upload, Star, Loader2, Wand2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { resumeService } from '@/services/resume.service'
import { ResumeUploader } from '@/components/resume/ResumeUploader'
import { ResumeCard } from '@/components/resume/ResumeCard'
import { ATSAnalysis } from '@/components/resume/ATSAnalysis'
import { ResumeIntelligence } from '@/components/resume/ResumeIntelligence'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import type { Resume, ATSScore } from '@/types'

export default function ResumePage() {
  const queryClient = useQueryClient()
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('analysis')
  const [showUploader, setShowUploader] = useState(false)
  const [jobDescription, setJobDescription] = useState('')
  const [optimizeResult, setOptimizeResult] = useState<{ optimized_content: string; ats_score: ATSScore } | null>(null)

  const { data: resumesData, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeService.getResumes(),
  })

  const resumes = resumesData?.items ?? []
  const selectedResume = resumes.find((r) => r.id === selectedResumeId) ?? resumes[0] ?? null

  const optimizeMutation = useMutation({
    mutationFn: ({ id, jd }: { id: string; jd: string }) =>
      resumeService.optimizeResume(id, jd),
    onSuccess: (data) => {
      setOptimizeResult(data)
      toast.success('Resume optimized!')
    },
    onError: () => toast.error('Optimization failed. Please try again.'),
  })

  const setPrimaryMutation = useMutation({
    mutationFn: (id: string) => resumeService.setPrimary(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      toast.success('Set as primary resume')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumeService.deleteResume(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] })
      toast.success('Resume deleted')
    },
  })

  const handleUploadSuccess = (resume: Resume) => {
    queryClient.invalidateQueries({ queryKey: ['resumes'] })
    setSelectedResumeId(resume.id)
    setShowUploader(false)
    toast.success('Resume uploaded and analyzed!')
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Skeleton className="h-40 rounded-xl" />
          <Skeleton className="lg:col-span-2 h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 pb-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Resume Manager</h1>
        <Button
          variant="primary"
          size="sm"
          leftIcon={<Upload className="w-4 h-4" />}
          onClick={() => setShowUploader((v) => !v)}
        >
          Upload New
        </Button>
      </div>

      {/* Upload area */}
      {(showUploader || resumes.length === 0) && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          <ResumeUploader onSuccess={handleUploadSuccess} compact={resumes.length > 0} />
        </motion.div>
      )}

      {resumes.length === 0 && !showUploader && (
        <EmptyState
          icon={<FileText className="w-6 h-6" />}
          title="No resumes yet"
          description="Upload your first resume to get AI analysis, ATS scores, and job matching."
          action={{ label: 'Upload Resume', onClick: () => setShowUploader(true) }}
        />
      )}

      {resumes.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: versions list */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Resume Versions ({resumes.length})
            </p>
            {resumes.map((resume) => (
              <ResumeCard
                key={resume.id}
                resume={resume}
                isSelected={selectedResume?.id === resume.id}
                onSelect={() => setSelectedResumeId(resume.id)}
                onSetPrimary={() => setPrimaryMutation.mutate(resume.id)}
                onDelete={() => deleteMutation.mutate(resume.id)}
              />
            ))}
          </div>

          {/* Right: tabs */}
          <div className="lg:col-span-2">
            {selectedResume ? (
              <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
                <Tabs.List className="flex gap-1 p-1 bg-white/5 rounded-xl border border-white/10 mb-4">
                  {[
                    { value: 'analysis', label: 'ATS Analysis', icon: <Star className="w-3.5 h-3.5" /> },
                    { value: 'intelligence', label: 'Intelligence', icon: <FileText className="w-3.5 h-3.5" /> },
                    { value: 'optimize', label: 'Optimize', icon: <Wand2 className="w-3.5 h-3.5" /> },
                  ].map((tab) => (
                    <Tabs.Trigger
                      key={tab.value}
                      value={tab.value}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-all
                        text-slate-400 hover:text-slate-200
                        data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-300 data-[state=active]:border data-[state=active]:border-indigo-500/30"
                    >
                      {tab.icon}
                      {tab.label}
                    </Tabs.Trigger>
                  ))}
                </Tabs.List>

                <Tabs.Content value="analysis">
                  {selectedResume.analysis?.ats_score ? (
                    <ATSAnalysis atsScore={selectedResume.analysis.ats_score} />
                  ) : (
                    <EmptyState
                      icon={<Star className="w-5 h-5" />}
                      title="No ATS analysis yet"
                      description="Analysis will appear here after processing."
                    />
                  )}
                </Tabs.Content>

                <Tabs.Content value="intelligence">
                  {selectedResume.analysis ? (
                    <ResumeIntelligence analysis={selectedResume.analysis} />
                  ) : (
                    <EmptyState
                      icon={<FileText className="w-5 h-5" />}
                      title="No intelligence data"
                      description="Resume intelligence will appear after analysis completes."
                    />
                  )}
                </Tabs.Content>

                <Tabs.Content value="optimize">
                  <div className="glass-card p-5 space-y-4">
                    <h3 className="text-sm font-semibold text-slate-300">Optimize for a Job</h3>
                    <p className="text-xs text-slate-400">
                      Paste a job description and our AI will rewrite your resume to maximize ATS score.
                    </p>
                    <textarea
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the full job description here..."
                      rows={8}
                      className="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                    <Button
                      variant="primary"
                      leftIcon={optimizeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                      isLoading={optimizeMutation.isPending}
                      disabled={!jobDescription.trim() || optimizeMutation.isPending}
                      onClick={() => {
                        if (selectedResume && jobDescription.trim()) {
                          optimizeMutation.mutate({ id: selectedResume.id, jd: jobDescription.trim() })
                        }
                      }}
                    >
                      Optimize Resume
                    </Button>

                    {optimizeResult && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold text-slate-300">Optimized Result</p>
                          <span className="text-xs font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
                            ATS: {optimizeResult.ats_score.overall}%
                          </span>
                        </div>
                        <div className="bg-white/3 border border-white/10 rounded-xl p-4 max-h-64 overflow-y-auto">
                          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                            {optimizeResult.optimized_content}
                          </pre>
                        </div>
                      </motion.div>
                    )}
                  </div>
                </Tabs.Content>
              </Tabs.Root>
            ) : (
              <EmptyState
                icon={<FileText className="w-5 h-5" />}
                title="Select a resume"
                description="Choose a resume from the left panel to view analysis."
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
