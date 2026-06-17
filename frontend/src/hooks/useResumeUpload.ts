import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { resumeService } from '@/services/resume.service'
import type { Resume } from '@/types'
import toast from 'react-hot-toast'

type UploadStatus = 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error'

interface UseResumeUploadReturn {
  uploadStatus: UploadStatus
  uploadProgress: number
  uploadedResume: Resume | null
  isDragActive: boolean
  getRootProps: ReturnType<typeof useDropzone>['getRootProps']
  getInputProps: ReturnType<typeof useDropzone>['getInputProps']
  reset: () => void
  uploadFile: (file: File) => Promise<Resume | null>
}

export const useResumeUpload = (onSuccess?: (resume: Resume) => void): UseResumeUploadReturn => {
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedResume, setUploadedResume] = useState<Resume | null>(null)

  const uploadFile = useCallback(
    async (file: File): Promise<Resume | null> => {
      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
      ]
      if (!allowedTypes.includes(file.type)) {
        toast.error('Please upload a PDF, DOCX, or TXT file')
        return null
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error('File size must be less than 10MB')
        return null
      }

      setUploadStatus('uploading')
      setUploadProgress(0)

      try {
        const resume = await resumeService.uploadResume(file, (progress) => {
          setUploadProgress(progress)
          if (progress === 100) {
            setUploadStatus('analyzing')
          }
        })

        setUploadedResume(resume)
        setUploadStatus('complete')
        toast.success('Resume uploaded and analyzed successfully!')
        onSuccess?.(resume)
        return resume
      } catch {
        setUploadStatus('error')
        toast.error('Failed to upload resume. Please try again.')
        return null
      }
    },
    [onSuccess]
  )

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        uploadFile(acceptedFiles[0])
      }
    },
    [uploadFile]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    disabled: uploadStatus === 'uploading' || uploadStatus === 'analyzing',
  })

  const reset = useCallback(() => {
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadedResume(null)
  }, [])

  return {
    uploadStatus,
    uploadProgress,
    uploadedResume,
    isDragActive,
    getRootProps,
    getInputProps,
    reset,
    uploadFile,
  }
}
