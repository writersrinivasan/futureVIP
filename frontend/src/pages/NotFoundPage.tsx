import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Home, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/common/Button'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center px-4">
      <div className="text-center">
        {/* 404 large text */}
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        >
          <motion.h1
            animate={{ y: [0, -16, 0] }}
            transition={{ repeat: Infinity, duration: 2.4, ease: 'easeInOut' }}
            className="text-[10rem] font-black leading-none bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent select-none"
          >
            404
          </motion.h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="mt-4 mb-10"
        >
          <h2 className="text-2xl font-bold text-slate-200 mb-3">Page Not Found</h2>
          <p className="text-slate-400 max-w-sm mx-auto leading-relaxed">
            The page you were looking for doesn't exist or may have been moved. Let's get you back on track.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="flex flex-col sm:flex-row gap-3 justify-center"
        >
          <Button
            variant="primary"
            size="lg"
            leftIcon={<Home className="w-4 h-4" />}
            onClick={() => navigate('/dashboard')}
          >
            Go to Dashboard
          </Button>
          <Button
            variant="ghost"
            size="lg"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            onClick={() => navigate(-1)}
          >
            Go Back
          </Button>
        </motion.div>
      </div>
    </div>
  )
}
