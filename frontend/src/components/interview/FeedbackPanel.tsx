import { useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, AlertTriangle, ChevronDown, ChevronUp, ArrowRight, Tag } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { Progress } from '@/components/common/Progress'
import { cn } from '@/utils/cn'
import type { InterviewFeedback } from '@/types'

interface FeedbackPanelProps {
  feedback: InterviewFeedback
  onNext: () => void
  isLast?: boolean
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-amber-400'
  return 'text-red-400'
}

const getScoreRingColor = (score: number) => {
  if (score >= 80) return 'stroke-green-400'
  if (score >= 60) return 'stroke-amber-400'
  return 'stroke-red-400'
}

const ScoreCircle = ({ score }: { score: number }) => {
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative w-28 h-28 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
        <motion.circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
          className={getScoreRingColor(score)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, type: 'spring' }}
          className={cn('text-2xl font-bold', getScoreColor(score))}
        >
          {score}
        </motion.span>
        <span className="text-xs text-slate-500 font-medium">/ 100</span>
      </div>
    </div>
  )
}

export const FeedbackPanel = ({ feedback, onNext, isLast = false }: FeedbackPanelProps) => {
  const [exampleOpen, setExampleOpen] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      {/* Score + header */}
      <div className="glass-card p-6">
        <h3 className="text-center text-sm font-medium text-slate-400 mb-4">AI Feedback Score</h3>
        <ScoreCircle score={feedback.score} />
        <p className="text-center text-xs text-slate-500 mt-3">
          {feedback.score >= 80
            ? 'Excellent answer!'
            : feedback.score >= 60
            ? 'Good — room to improve'
            : 'Needs more detail and structure'}
        </p>
      </div>

      {/* Strengths */}
      {feedback.strengths.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-400" />
            Strengths
          </h4>
          <ul className="space-y-2">
            {feedback.strengths.map((s, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-start gap-2 text-sm text-slate-300"
              >
                <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                {s}
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Improvements */}
      {feedback.improvements.length > 0 && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Areas to Improve
          </h4>
          <ul className="space-y-2">
            {feedback.improvements.map((imp, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-start gap-2 text-sm text-slate-300"
              >
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                {imp}
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* STAR breakdown */}
      {feedback.star_breakdown && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">STAR Breakdown</h4>
          <div className="space-y-2.5">
            {Object.entries(feedback.star_breakdown).map(([key, val]) => (
              <div key={key}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400 capitalize">{key}</span>
                  <span className={val.present ? 'text-green-400' : 'text-red-400'}>
                    {val.present ? `${Math.round(val.quality * 10)}%` : 'Missing'}
                  </span>
                </div>
                <Progress
                  value={val.present ? val.quality * 10 : 0}
                  size="sm"
                  variant={val.present ? (val.quality >= 7 ? 'success' : 'warning') : 'danger'}
                  animated
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Keywords */}
      {(feedback.keywords_used.length > 0 || feedback.missing_keywords.length > 0) && (
        <div className="glass-card p-5">
          <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Tag className="w-4 h-4 text-indigo-400" />
            Keywords
          </h4>
          {feedback.keywords_used.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-slate-500 mb-1.5">Used ({feedback.keywords_used.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {feedback.keywords_used.map((kw) => (
                  <span key={kw} className="text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-300 border border-green-500/20">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          {feedback.missing_keywords.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1.5">Missing ({feedback.missing_keywords.length})</p>
              <div className="flex flex-wrap gap-1.5">
                {feedback.missing_keywords.map((kw) => (
                  <span key={kw} className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-300 border border-red-500/20">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Example answer collapsible */}
      <div className="glass-card overflow-hidden">
        <button
          onClick={() => setExampleOpen((o) => !o)}
          className="w-full flex items-center justify-between p-5 text-left hover:bg-white/5 transition-colors"
        >
          <span className="text-sm font-semibold text-slate-300">Example Answer</span>
          {exampleOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>
        {exampleOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-5 pb-5"
          >
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
              {feedback.example_answer}
            </p>
          </motion.div>
        )}
      </div>

      {/* Next button */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        rightIcon={<ArrowRight className="w-4 h-4" />}
        onClick={onNext}
      >
        {isLast ? 'Finish Session' : 'Next Question'}
      </Button>
    </motion.div>
  )
}
