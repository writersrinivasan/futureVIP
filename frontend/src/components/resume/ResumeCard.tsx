import { motion } from 'framer-motion'
import { FileText, Download, Trash2, Star, StarOff, Clock, BarChart2 } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { ATSGauge } from '@/components/dashboard/ATSGauge'
import { formatDate } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { Resume } from '@/types'

interface ResumeCardProps {
  resume: Resume
  isSelected?: boolean
  onSelect?: () => void
  onDelete?: () => void
  onSetPrimary?: () => void
  onDownload?: () => void
  index?: number
}

export const ResumeCard = ({
  resume,
  isSelected,
  onSelect,
  onDelete,
  onSetPrimary,
  onDownload,
  index = 0,
}: ResumeCardProps) => {
  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.pdf')) return '📄'
    if (filename.endsWith('.docx') || filename.endsWith('.doc')) return '📝'
    return '📃'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={cn(
        'glass-card p-4 cursor-pointer transition-all duration-300',
        isSelected
          ? 'border-primary-500/50 bg-primary-500/5'
          : 'hover:border-white/20 hover:bg-white/8'
      )}
      onClick={onSelect}
    >
      <div className="flex gap-4">
        {/* File icon & gauge */}
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-2xl">
            {getFileIcon(resume.filename)}
          </div>
          {resume.ats_score !== undefined && (
            <ATSGauge score={resume.ats_score} size="sm" showLabel={false} />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200 truncate">{resume.filename}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="default" size="sm">v{resume.version}</Badge>
                {resume.is_primary && (
                  <Badge variant="success" size="sm" dot>Primary</Badge>
                )}
                {resume.ats_score !== undefined && (
                  <Badge
                    variant={resume.ats_score >= 80 ? 'success' : resume.ats_score >= 60 ? 'warning' : 'danger'}
                    size="sm"
                  >
                    {resume.ats_score}% ATS
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <FileText className="w-4 h-4 text-slate-500" />
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
            <Clock className="w-3 h-3" />
            <span>Uploaded {formatDate(resume.created_at)}</span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            {onDownload && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<Download className="w-3.5 h-3.5" />}
                onClick={onDownload}
                className="text-xs py-1"
              >
                Download
              </Button>
            )}
            {!resume.is_primary && onSetPrimary && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<Star className="w-3.5 h-3.5" />}
                onClick={onSetPrimary}
                className="text-xs py-1 text-warning-400 hover:text-warning-300"
              >
                Set Primary
              </Button>
            )}
            {resume.is_primary && (
              <span className="flex items-center gap-1 text-xs text-success-400 px-2">
                <StarOff className="w-3.5 h-3.5" />
                Primary
              </span>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                onClick={onDelete}
                className="text-xs py-1 text-danger-400 hover:text-danger-300 hover:bg-danger-500/10 ml-auto"
              >
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Selected indicator */}
      {isSelected && (
        <motion.div
          layoutId="selected-resume"
          className="mt-3 h-0.5 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-full"
        />
      )}
    </motion.div>
  )
}
