import { motion } from 'framer-motion'
import { CheckCircle, XCircle, AlertCircle, Lightbulb, Download } from 'lucide-react'
import { ATSGauge } from '@/components/dashboard/ATSGauge'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import type { ATSScore } from '@/types'

interface ATSAnalysisProps {
  atsScore: ATSScore
  onOptimize?: () => void
  onDownloadOptimized?: () => void
}

export const ATSAnalysis = ({ atsScore, onOptimize, onDownloadOptimized }: ATSAnalysisProps) => {
  return (
    <div className="space-y-6">
      {/* Score overview */}
      <div className="flex flex-col md:flex-row gap-6 items-center">
        <ATSGauge score={atsScore.overall} size="lg" />
        <div className="flex-1 grid grid-cols-2 gap-3">
          {[
            { label: 'Keyword Match', value: atsScore.keyword_match },
            { label: 'Format Score', value: atsScore.format_score },
            { label: 'Readability', value: atsScore.readability_score },
            { label: 'Completeness', value: atsScore.section_completeness },
          ].map((item) => (
            <div key={item.label} className="bg-white/5 rounded-xl p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-slate-400">{item.label}</span>
                <span className={`text-xs font-bold ${
                  item.value >= 80 ? 'text-success-400' :
                  item.value >= 60 ? 'text-warning-400' : 'text-danger-400'
                }`}>
                  {item.value}%
                </span>
              </div>
              <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.value}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    item.value >= 80 ? 'bg-success-500' :
                    item.value >= 60 ? 'bg-warning-500' : 'bg-danger-500'
                  }`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Matching Keywords */}
      {atsScore.matching_keywords.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-success-400" />
            <h4 className="text-sm font-semibold text-slate-200">
              Matching Keywords ({atsScore.matching_keywords.length})
            </h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {atsScore.matching_keywords.map((keyword) => (
              <Badge key={keyword} variant="success" size="sm">{keyword}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Missing Keywords */}
      {atsScore.missing_keywords.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <XCircle className="w-4 h-4 text-danger-400" />
            <h4 className="text-sm font-semibold text-slate-200">
              Missing Keywords ({atsScore.missing_keywords.length})
            </h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {atsScore.missing_keywords.map((keyword) => (
              <Badge key={keyword} variant="danger" size="sm">{keyword}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {atsScore.suggestions.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-warning-400" />
            <h4 className="text-sm font-semibold text-slate-200">
              Improvement Suggestions
            </h4>
          </div>
          <div className="space-y-2">
            {atsScore.suggestions.map((suggestion, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex gap-2.5 p-3 bg-warning-500/5 border border-warning-500/20 rounded-xl"
              >
                <AlertCircle className="w-4 h-4 text-warning-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-slate-300">{suggestion}</p>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        {onOptimize && (
          <Button
            variant="primary"
            leftIcon={<AlertCircle className="w-4 h-4" />}
            onClick={onOptimize}
          >
            Optimize Resume
          </Button>
        )}
        {atsScore.optimized_content && onDownloadOptimized && (
          <Button
            variant="outline"
            leftIcon={<Download className="w-4 h-4" />}
            onClick={onDownloadOptimized}
          >
            Download Optimized
          </Button>
        )}
      </div>
    </div>
  )
}
