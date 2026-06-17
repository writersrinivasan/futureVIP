import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, CheckCircle } from 'lucide-react'
import { LoginForm } from '@/components/auth/LoginForm'
import { useAuthStore } from '@/store/auth.store'
import { useEffect } from 'react'

const FEATURES = [
  'AI-powered resume analysis & ATS optimization',
  'Semantic job matching across 2M+ listings',
  'Personalized career roadmaps with milestones',
  'Mock interviews with instant AI feedback',
]

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated } = useAuthStore()

  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname ?? '/dashboard'

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, from])

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex">
      {/* Left: Branding panel */}
      <motion.div
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-indigo-900/60 via-violet-900/40 to-[#0f0f1a] flex-col justify-between p-12"
      >
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-80 h-80 bg-indigo-600/25 rounded-full blur-[100px]" />
          <div className="absolute bottom-1/4 right-1/3 w-64 h-64 bg-violet-600/20 rounded-full blur-[80px]" />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-black text-xl text-white tracking-tight">FUTURE VIP</span>
        </div>

        {/* Center copy */}
        <div className="relative">
          <h2 className="text-4xl font-black text-white mb-4 leading-tight">
            Your AI Career Team,
            <br />
            <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Always On.
            </span>
          </h2>
          <p className="text-slate-400 mb-8 leading-relaxed">
            13 specialized AI agents working around the clock to accelerate your career journey.
          </p>
          <ul className="space-y-3">
            {FEATURES.map((f, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="flex items-center gap-3 text-sm text-slate-300"
              >
                <CheckCircle className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                {f}
              </motion.li>
            ))}
          </ul>
        </div>

        {/* Bottom quote */}
        <div className="relative">
          <p className="text-xs text-slate-500">
            "50,000+ job seekers found their dream role with FUTURE VIP"
          </p>
        </div>
      </motion.div>

      {/* Right: Login form */}
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex items-center justify-center px-6 py-12"
      >
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-black text-lg text-white">FUTURE VIP</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">Welcome back</h1>
            <p className="text-slate-400 text-sm">Sign in to your account to continue</p>
          </div>

          <LoginForm />
        </div>
      </motion.div>
    </div>
  )
}
