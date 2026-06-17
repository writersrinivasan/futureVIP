import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Clock, Send } from 'lucide-react'
import { Button } from '@/components/common/Button'

const MAX_CHARS = 2000
const MIN_CHARS = 20

const STAR_CHIPS = [
  { label: 'Situation', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  { label: 'Task', color: 'bg-violet-500/20 text-violet-300 border-violet-500/30' },
  { label: 'Action', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
  { label: 'Result', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
]

interface AnswerInputProps {
  onSubmit: (answer: string) => void
  isSubmitting?: boolean
}

export const AnswerInput = ({ onSubmit, isSubmitting = false }: AnswerInputProps) => {
  const [answer, setAnswer] = useState('')
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    setAnswer('')
    setSeconds(0)
  }, [])

  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  const canSubmit = answer.trim().length >= MIN_CHARS && !isSubmitting

  const handleSubmit = useCallback(() => {
    if (canSubmit) {
      onSubmit(answer.trim())
    }
  }, [answer, canSubmit, onSubmit])

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay: 0.1 }}
      className="glass-card p-6"
    >
      {/* Timer + STAR chips row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {STAR_CHIPS.map((chip) => (
            <span
              key={chip.label}
              className={`text-xs font-medium px-2.5 py-1 rounded-full border ${chip.color}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-1.5 text-sm font-mono text-slate-400 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
          <Clock className="w-3.5 h-3.5" />
          {formatTime(seconds)}
        </div>
      </div>

      {/* Textarea */}
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value.slice(0, MAX_CHARS))}
        placeholder="Share your experience using the STAR method... Describe the Situation, your Task, the Actions you took, and the Result you achieved."
        rows={8}
        className="w-full bg-white/5 border border-white/10 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/30 transition-all"
      />

      {/* Footer row */}
      <div className="flex items-center justify-between mt-3">
        <span
          className={`text-xs font-medium ${
            answer.length > MAX_CHARS * 0.9
              ? 'text-amber-400'
              : answer.length < MIN_CHARS && answer.length > 0
              ? 'text-red-400'
              : 'text-slate-500'
          }`}
        >
          {answer.length} / {MAX_CHARS} characters
          {answer.length > 0 && answer.length < MIN_CHARS && (
            <span className="ml-2 text-red-400">
              ({MIN_CHARS - answer.length} more needed)
            </span>
          )}
        </span>

        <Button
          variant="primary"
          size="md"
          leftIcon={<Send className="w-4 h-4" />}
          onClick={handleSubmit}
          disabled={!canSubmit}
          isLoading={isSubmitting}
        >
          Submit Answer
        </Button>
      </div>
    </motion.div>
  )
}
