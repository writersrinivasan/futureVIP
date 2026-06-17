import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, TrendingUp, Users, Award } from 'lucide-react'
import { RegisterForm } from '@/components/auth/RegisterForm'
import { useAuthStore } from '@/store/auth.store'
import { useEffect } from 'react'

const HIGHLIGHTS = [
  { icon: <TrendingUp className="w-4 h-4" />, text: '94% interview success rate' },
  { icon: <Users className="w-4 h-4" />, text: '50,000+ active users' },
  { icon: <Award className="w-4 h-4" />, text: 'Free to start, no credit card' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex flex-row-reverse">
      {/* Right: Branding panel */}
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-bl from-violet-900/60 via-indigo-900/40 to-[#0f0f1a] flex-col justify-between p-12"
      >
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-600/25 rounded-full blur-[100px]" />
          <div className="absolute bottom-1/4 left-1/3 w-64 h-64 bg-indigo-600/20 rounded-full blur-[80px]" />
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
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/15 border border-violet-500/25 text-violet-300 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            Join 50,000+ career starters
          </div>
          <h2 className="text-4xl font-black text-white mb-4 leading-tight">
            Your Dream Job
            <br />
            <span className="bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Starts Here.
            </span>
          </h2>
          <p className="text-slate-400 mb-8 leading-relaxed">
            Create your free account and let 13 AI agents work around the clock to find, match, and land your perfect role.
          </p>

          {/* Highlights */}
          <div className="space-y-3">
            {HIGHLIGHTS.map((h, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="flex items-center gap-3 text-sm text-slate-300"
              >
                <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center text-violet-400">
                  {h.icon}
                </div>
                {h.text}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Bottom */}
        <div className="relative">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <p className="text-sm text-slate-300 italic">
              "I went from 0 callbacks to 3 offers in 60 days using FUTURE VIP. The AI resume optimizer is incredible."
            </p>
            <p className="text-xs text-slate-500 mt-2">— James Liu, Senior Engineer @ Airbnb</p>
          </div>
        </div>
      </motion.div>

      {/* Left: Register form */}
      <motion.div
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex items-center justify-center px-6 py-12 overflow-y-auto"
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
            <h1 className="text-2xl font-bold text-white mb-2">Create your account</h1>
            <p className="text-slate-400 text-sm">Free forever. Upgrade anytime.</p>
          </div>

          <RegisterForm />
        </div>
      </motion.div>
    </div>
  )
}
