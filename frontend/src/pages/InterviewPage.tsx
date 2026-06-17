import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Plus, Trophy, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { interviewService } from '@/services/interview.service'
import { jobsService } from '@/services/jobs.service'
import { QuestionCard } from '@/components/interview/QuestionCard'
import { AnswerInput } from '@/components/interview/AnswerInput'
import { FeedbackPanel } from '@/components/interview/FeedbackPanel'
import { SessionHistory } from '@/components/interview/SessionHistory'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { Badge } from '@/components/common/Badge'
import { Progress } from '@/components/common/Progress'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import type { InterviewSession, InterviewQuestion } from '@/types'

type SessionView = 'list' | 'active' | 'complete'

export default function InterviewPage() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<SessionView>('list')
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null)
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0)
  const [showFeedback, setShowFeedback] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)

  // New session form state
  const [sessionType, setSessionType] = useState<'technical' | 'behavioral' | 'mixed'>('behavioral')
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [numQuestions, setNumQuestions] = useState(5)
  const [targetJobId, setTargetJobId] = useState('')

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['interview-sessions'],
    queryFn: () => interviewService.getSessions(),
  })

  const { data: jobsData } = useQuery({
    queryKey: ['jobs-list'],
    queryFn: () => jobsService.getJobs({ per_page: 20 }),
  })

  const startMutation = useMutation({
    mutationFn: () =>
      interviewService.startSession({
        session_type: sessionType,
        difficulty,
        num_questions: numQuestions,
        ...(targetJobId ? { job_id: targetJobId } : {}),
      }),
    onSuccess: (session) => {
      setActiveSession(session)
      setCurrentQuestionIdx(0)
      setShowFeedback(false)
      setView('active')
      setShowNewModal(false)
      queryClient.invalidateQueries({ queryKey: ['interview-sessions'] })
      toast.success('Interview session started!')
    },
    onError: () => toast.error('Failed to start session.'),
  })

  const answerMutation = useMutation({
    mutationFn: ({ sessionId, questionId, answer }: { sessionId: string; questionId: string; answer: string }) =>
      interviewService.submitAnswer(sessionId, questionId, answer),
    onSuccess: (feedback) => {
      // Merge feedback into the current question inside the active session
      setActiveSession((prev) => {
        if (!prev) return null
        const updatedQuestions = prev.questions.map((q, idx) =>
          idx === currentQuestionIdx ? { ...q, feedback, answer: 'submitted' } : q
        )
        return { ...prev, questions: updatedQuestions }
      })
      setShowFeedback(true)
    },
    onError: () => toast.error('Failed to submit answer.'),
  })

  const sessions = sessionsData?.items ?? []
  const currentQuestion: InterviewQuestion | undefined = activeSession?.questions?.[currentQuestionIdx]
  const isLastQuestion = activeSession ? currentQuestionIdx >= (activeSession.total_questions - 1) : false
  const answeredCurrent = !!currentQuestion?.answer

  const handleNextQuestion = () => {
    if (isLastQuestion) {
      setView('complete')
    } else {
      setCurrentQuestionIdx((i) => i + 1)
      setShowFeedback(false)
    }
  }

  const handleResumeSession = (session: InterviewSession) => {
    setActiveSession(session)
    const nextUnanswered = session.questions.findIndex((q) => !q.answer)
    setCurrentQuestionIdx(nextUnanswered === -1 ? session.questions.length - 1 : nextUnanswered)
    setShowFeedback(false)
    setView('active')
  }

  return (
    <div className="flex h-full gap-0 -mx-6 -mt-6">
      {/* Sessions sidebar */}
      <div className="w-80 flex-shrink-0 border-r border-white/10 flex flex-col">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Sessions</h2>
          <Button size="sm" variant="primary" onClick={() => setShowNewModal(true)} leftIcon={<Plus className="w-3.5 h-3.5" />}>
            New
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-center px-4">
              <MessageSquare className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-xs text-slate-500">No sessions yet. Start your first mock interview!</p>
            </div>
          ) : (
            <SessionHistory
              sessions={sessions}
              activeSessionId={activeSession?.id}
              onSelect={handleResumeSession}
            />
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden p-6">
        <AnimatePresence mode="wait">
          {view === 'list' && !activeSession && (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex-1 flex items-center justify-center"
            >
              <EmptyState
                icon={<MessageSquare className="w-10 h-10 text-indigo-400" />}
                title="Ready to practice?"
                description="Start a mock interview session to practice your answers and get AI-powered feedback."
                action={{ label: 'Start Interview', onClick: () => setShowNewModal(true) }}
              />
            </motion.div>
          )}

          {view === 'active' && activeSession && currentQuestion && (
            <motion.div
              key="active"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex-1 flex flex-col gap-4 overflow-y-auto"
            >
              {/* Progress bar */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">
                    Question {currentQuestionIdx + 1} of {activeSession.total_questions}
                  </span>
                  <Badge variant={difficulty === 'easy' ? 'success' : difficulty === 'medium' ? 'warning' : 'danger'} size="sm">
                    {sessionType} · {difficulty}
                  </Badge>
                </div>
                <Progress
                  value={Math.round(((currentQuestionIdx + (answeredCurrent ? 1 : 0)) / activeSession.total_questions) * 100)}
                  variant="primary"
                  size="sm"
                />
              </div>

              <QuestionCard
                question={currentQuestion}
                questionNumber={currentQuestionIdx + 1}
                totalQuestions={activeSession.total_questions}
              />

              {!showFeedback ? (
                <AnswerInput
                  isSubmitting={answerMutation.isPending}
                  onSubmit={(answer) =>
                    answerMutation.mutate({
                      sessionId: activeSession.id,
                      questionId: currentQuestion.id,
                      answer,
                    })
                  }
                />
              ) : (
                currentQuestion.feedback && (
                  <FeedbackPanel
                    feedback={currentQuestion.feedback}
                    onNext={handleNextQuestion}
                    isLast={isLastQuestion}
                  />
                )
              )}
            </motion.div>
          )}

          {view === 'complete' && activeSession && (
            <motion.div
              key="complete"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex-1 flex items-center justify-center"
            >
              <div className="text-center max-w-sm">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mx-auto mb-4">
                  <Trophy className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Session Complete!</h2>
                {activeSession.overall_score != null && (
                  <p className="text-4xl font-black text-indigo-400 mb-2">
                    {Math.round(activeSession.overall_score)}
                    <span className="text-lg text-slate-500">/100</span>
                  </p>
                )}
                <p className="text-sm text-slate-400 mb-6">
                  You answered {activeSession.total_questions} questions in this session.
                </p>
                <div className="flex flex-col sm:flex-row gap-2 justify-center">
                  <Button variant="primary" onClick={() => setShowNewModal(true)} leftIcon={<Plus className="w-4 h-4" />}>
                    New Session
                  </Button>
                  <Button variant="ghost" onClick={() => { setView('list'); setActiveSession(null); }}>
                    Back to Sessions
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* New Session Modal */}
      <Modal open={showNewModal} onClose={() => setShowNewModal(false)} title="Start New Interview Session">
        <div className="space-y-4 p-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Session Type</label>
            <div className="grid grid-cols-3 gap-2">
              {(['behavioral', 'technical', 'mixed'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setSessionType(t)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                    sessionType === t
                      ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                      : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                  }`}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Difficulty</label>
            <div className="grid grid-cols-3 gap-2">
              {(['easy', 'medium', 'hard'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                    difficulty === d
                      ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                      : 'border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                  }`}
                >
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Questions: <span className="text-indigo-400">{numQuestions}</span>
            </label>
            <input
              type="range"
              min={3}
              max={15}
              step={1}
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
          </div>

          {jobsData?.items && jobsData.items.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Job (optional)</label>
              <select
                value={targetJobId}
                onChange={(e) => setTargetJobId(e.target.value)}
                className="input-field text-sm"
              >
                <option value="">General interview</option>
                {jobsData.items.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} — {job.company}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button
              variant="primary"
              onClick={() => startMutation.mutate()}
              isLoading={startMutation.isPending}
              className="flex-1"
              rightIcon={<ChevronRight className="w-4 h-4" />}
            >
              Start Session
            </Button>
            <Button variant="ghost" onClick={() => setShowNewModal(false)}>Cancel</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
