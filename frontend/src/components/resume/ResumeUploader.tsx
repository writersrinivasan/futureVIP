import { motion, AnimatePresence } from 'framer-motion'
import { Upload, File, CheckCircle, XCircle, Loader2, UploadCloud } from 'lucide-react'
import { useResumeUpload } from '@/hooks/useResumeUpload'
import { Progress } from '@/components/common/Progress'
import { Button } from '@/components/common/Button'
import type { Resume } from '@/types'

interface ResumeUploaderProps {
  onSuccess?: (resume: Resume) => void
  compact?: boolean
}

export const ResumeUploader = ({ onSuccess, compact = false }: ResumeUploaderProps) => {
  const {
    uploadStatus,
    uploadProgress,
    uploadedResume,
    isDragActive,
    getRootProps,
    getInputProps,
    reset,
  } = useResumeUpload(onSuccess)

  const isIdle = uploadStatus === 'idle'
  const isUploading = uploadStatus === 'uploading'
  const isAnalyzing = uploadStatus === 'analyzing'
  const isComplete = uploadStatus === 'complete'
  const isError = uploadStatus === 'error'

  return (
    <div className="w-full">
      <AnimatePresence mode="wait">
        {(isIdle || isDragActive) && (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
          <div
            {...getRootProps()}
            className={`
              relative border-2 border-dashed rounded-2xl transition-all duration-300 cursor-pointer
              ${isDragActive
                ? 'border-primary-400 bg-primary-500/10 scale-[1.01]'
                : 'border-white/20 hover:border-primary-500/50 hover:bg-white/3'}
              ${compact ? 'p-6' : 'p-10'}
            `}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center text-center">
              <motion.div
                animate={isDragActive ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
                className={`
                  rounded-2xl flex items-center justify-center mb-4
                  ${isDragActive ? 'bg-primary-500/20 text-primary-400' : 'bg-white/5 text-slate-400'}
                  ${compact ? 'w-12 h-12' : 'w-16 h-16'}
                `}
              >
                {isDragActive ? (
                  <UploadCloud className={compact ? 'w-6 h-6' : 'w-8 h-8'} />
                ) : (
                  <Upload className={compact ? 'w-6 h-6' : 'w-8 h-8'} />
                )}
              </motion.div>

              {isDragActive ? (
                <p className="text-primary-400 font-semibold text-lg">Drop it here!</p>
              ) : (
                <>
                  <p className={`font-semibold text-slate-200 mb-1 ${compact ? 'text-base' : 'text-lg'}`}>
                    {compact ? 'Upload Resume' : 'Drag & drop your resume'}
                  </p>
                  <p className="text-sm text-slate-400 mb-4">
                    {compact ? 'PDF, DOCX, or TXT' : 'or click to browse • PDF, DOCX, TXT • Max 10MB'}
                  </p>
                  {!compact && (
                    <Button variant="outline" size="sm">
                      Browse Files
                    </Button>
                  )}
                </>
              )}
            </div>

            {/* Corner decorations */}
            {!compact && (
              <>
                <div className="absolute top-3 left-3 w-5 h-5 border-l-2 border-t-2 border-primary-500/30 rounded-tl-lg" />
                <div className="absolute top-3 right-3 w-5 h-5 border-r-2 border-t-2 border-primary-500/30 rounded-tr-lg" />
                <div className="absolute bottom-3 left-3 w-5 h-5 border-l-2 border-b-2 border-primary-500/30 rounded-bl-lg" />
                <div className="absolute bottom-3 right-3 w-5 h-5 border-r-2 border-b-2 border-primary-500/30 rounded-br-lg" />
              </>
            )}
          </div>
          </motion.div>
        )}

        {(isUploading || isAnalyzing) && (
          <motion.div
            key="progress"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="border border-white/10 rounded-2xl p-8 bg-white/3"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/20 flex items-center justify-center mb-4">
                <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
              </div>
              <p className="font-semibold text-slate-200 mb-1">
                {isAnalyzing ? 'AI Analyzing Your Resume...' : 'Uploading Resume...'}
              </p>
              <p className="text-sm text-slate-400 mb-6">
                {isAnalyzing
                  ? 'Our AI is extracting insights, skills, and ATS score'
                  : 'Securely uploading your file'}
              </p>
              {isUploading && (
                <div className="w-full max-w-xs">
                  <Progress
                    value={uploadProgress}
                    showPercentage
                    variant="gradient"
                    animated={false}
                  />
                </div>
              )}
              {isAnalyzing && (
                <div className="flex gap-2 mt-2">
                  {['Parsing content', 'Extracting skills', 'Scoring ATS'].map((step, i) => (
                    <motion.span
                      key={step}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.5, repeat: Infinity, repeatDelay: 1.5 }}
                      className="text-xs text-slate-500 bg-white/5 px-2 py-1 rounded-full"
                    >
                      {step}
                    </motion.span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {isComplete && uploadedResume && (
          <motion.div
            key="complete"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="border border-success-500/30 rounded-2xl p-8 bg-success-500/5"
          >
            <div className="flex flex-col items-center text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                className="w-16 h-16 rounded-2xl bg-success-500/20 flex items-center justify-center mb-4"
              >
                <CheckCircle className="w-8 h-8 text-success-400" />
              </motion.div>
              <p className="font-semibold text-slate-200 mb-1">Upload Complete!</p>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
                <File className="w-4 h-4" />
                <span className="truncate max-w-[200px]">{uploadedResume.filename}</span>
              </div>
              {uploadedResume.ats_score !== undefined && (
                <div className="bg-white/5 rounded-xl px-4 py-2 mb-4">
                  <p className="text-xs text-slate-400">ATS Score</p>
                  <p className={`text-2xl font-bold ${
                    uploadedResume.ats_score >= 80 ? 'text-success-400' :
                    uploadedResume.ats_score >= 60 ? 'text-warning-400' : 'text-danger-400'
                  }`}>
                    {uploadedResume.ats_score}/100
                  </p>
                </div>
              )}
              <Button variant="outline" size="sm" onClick={reset}>
                Upload Another
              </Button>
            </div>
          </motion.div>
        )}

        {isError && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="border border-danger-500/30 rounded-2xl p-8 bg-danger-500/5"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-2xl bg-danger-500/20 flex items-center justify-center mb-4">
                <XCircle className="w-8 h-8 text-danger-400" />
              </div>
              <p className="font-semibold text-slate-200 mb-1">Upload Failed</p>
              <p className="text-sm text-slate-400 mb-4">
                Something went wrong. Please try again.
              </p>
              <Button variant="danger" size="sm" onClick={reset}>
                Try Again
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
