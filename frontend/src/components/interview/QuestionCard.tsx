import { motion } from 'framer-motion'
import { Lightbulb } from 'lucide-react'
import { Badge } from '@/components/common/Badge'
import type { InterviewQuestion } from '@/types'

interface QuestionCardProps {
  question: InterviewQuestion
  questionNumber: number
  totalQuestions: number
}

const typeColors: Record<string, 'primary' | 'secondary' | 'accent' | 'warning'> = {
  technical: 'primary',
  behavioral: 'secondary',
  situational: 'accent',
  case: 'warning',
}

const difficultyColors: Record<string, 'success' | 'warning' | 'danger'> = {
  easy: 'success',
  medium: 'warning',
  hard: 'danger',
}

export const QuestionCard = ({ question, questionNumber, totalQuestions }: QuestionCardProps) => {
  return (
    <motion.div
      key={question.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="glass-card p-6"
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-slate-400">
          Question{' '}
          <span className="text-indigo-400 font-bold">{questionNumber}</span>
          {' '}of{' '}
          <span className="text-slate-300 font-bold">{totalQuestions}</span>
        </span>
        <div className="flex items-center gap-2">
          <Badge variant={typeColors[question.question_type] ?? 'primary'} size="sm">
            {question.question_type.charAt(0).toUpperCase() + question.question_type.slice(1)}
          </Badge>
          <Badge variant={difficultyColors[question.difficulty] ?? 'warning'} size="sm">
            {question.difficulty.charAt(0).toUpperCase() + question.difficulty.slice(1)}
          </Badge>
          {question.category && (
            <Badge variant="outline" size="sm">
              {question.category}
            </Badge>
          )}
        </div>
      </div>

      {/* Question text */}
      <p className="text-lg font-semibold text-slate-100 leading-relaxed mb-4">
        {question.question_text}
      </p>

      {/* STAR tip for behavioral */}
      {question.question_type === 'behavioral' && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20"
        >
          <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-300 mb-1">STAR Format Tip</p>
            <p className="text-xs text-amber-200/80">
              Structure your answer using: <strong>Situation</strong> → <strong>Task</strong> → <strong>Action</strong> → <strong>Result</strong>. This method helps you give clear, structured responses that interviewers love.
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
