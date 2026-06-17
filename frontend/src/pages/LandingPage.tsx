import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useInView } from 'framer-motion'
import {
  Brain,
  Search,
  FileCheck,
  Map,
  Mic,
  Kanban,
  ArrowRight,
  Play,
  Star,
  CheckCircle,
  Zap,
  Github,
} from 'lucide-react'
import { Button } from '@/components/common/Button'

// ---- Animated counter ----
const useCountUp = (target: number, duration = 2000, startOnView = true) => {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })

  useEffect(() => {
    if (!inView && startOnView) return
    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(eased * target))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [inView, target, duration, startOnView])

  return { count, ref }
}

const StatItem = ({ value, suffix, label }: { value: number; suffix: string; label: string }) => {
  const { count, ref } = useCountUp(value)
  return (
    <div className="text-center">
      <div className="text-3xl md:text-4xl font-black text-white mb-1">
        <span ref={ref}>{count.toLocaleString()}</span>
        <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          {suffix}
        </span>
      </div>
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  )
}

const FEATURES = [
  {
    icon: <Brain className="w-6 h-6" />,
    title: 'Resume Intelligence',
    desc: 'Deep AI analysis extracts insights beyond keywords — career trajectory, value proposition, hidden strengths.',
    color: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/20',
    iconColor: 'bg-indigo-500/20 text-indigo-400',
  },
  {
    icon: <Search className="w-6 h-6" />,
    title: 'Semantic Job Matching',
    desc: 'Vector embeddings find perfect matches humans miss — semantic relevance beyond keyword overlap.',
    color: 'from-violet-500/20 to-violet-500/5 border-violet-500/20',
    iconColor: 'bg-violet-500/20 text-violet-400',
  },
  {
    icon: <FileCheck className="w-6 h-6" />,
    title: 'ATS Optimization',
    desc: 'Score and rewrite your resume for every job application, maximizing your chances of passing filters.',
    color: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/20',
    iconColor: 'bg-cyan-500/20 text-cyan-400',
  },
  {
    icon: <Map className="w-6 h-6" />,
    title: 'Career Roadmapping',
    desc: 'Personalized 90-day plans to your target role with curated resources and milestone tracking.',
    color: 'from-green-500/20 to-green-500/5 border-green-500/20',
    iconColor: 'bg-green-500/20 text-green-400',
  },
  {
    icon: <Mic className="w-6 h-6" />,
    title: 'Interview Coach',
    desc: 'AI-powered mock interviews with instant feedback, STAR analysis, and keyword gap detection.',
    color: 'from-amber-500/20 to-amber-500/5 border-amber-500/20',
    iconColor: 'bg-amber-500/20 text-amber-400',
  },
  {
    icon: <Kanban className="w-6 h-6" />,
    title: 'Application Tracking',
    desc: 'Kanban board with smart follow-up reminders and response rate analytics to stay organized.',
    color: 'from-pink-500/20 to-pink-500/5 border-pink-500/20',
    iconColor: 'bg-pink-500/20 text-pink-400',
  },
]

const HOW_IT_WORKS = [
  { step: '01', title: 'Upload Resume', desc: 'Drop your PDF resume. Our AI instantly parses and indexes your experience.' },
  { step: '02', title: 'AI Analysis', desc: '13 specialized agents analyze your skills, career trajectory, and market positioning.' },
  { step: '03', title: 'Job Discovery', desc: 'Semantic matching surfaces the best opportunities from thousands of live listings.' },
  { step: '04', title: 'Land Your Dream Job', desc: 'Optimize applications, ace interviews, and track every opportunity to success.' },
]

const TESTIMONIALS = [
  {
    name: 'Priya Sharma',
    role: 'Software Engineer → Senior SWE at Google',
    text: 'FUTURE VIP matched me to roles I would never have found myself. The ATS optimization alone got me past filters at FAANG companies.',
    score: 97,
  },
  {
    name: 'Marcus Chen',
    role: 'Data Analyst → Data Scientist at Stripe',
    text: 'The interview coach gave me feedback at 2am before my big interview. I walked in prepared and confident. Got the offer!',
    score: 91,
  },
  {
    name: "Sarah O'Brien",
    role: 'Marketing Manager → Product Manager',
    text: 'Career roadmapping showed me exactly which skills to build for a PM role. 90 days later, I had 3 offers.',
    score: 89,
  },
]

const TECH_STACK = [
  { name: 'OpenAI GPT-4o', icon: '🤖' },
  { name: 'Python FastAPI', icon: '⚡' },
  { name: 'React 18', icon: '⚛️' },
  { name: 'PostgreSQL', icon: '🐘' },
  { name: 'Redis', icon: '💾' },
  { name: 'Celery', icon: '🌿' },
]

const stagger = {
  container: { animate: { transition: { staggerChildren: 0.1 } } },
  item: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.5 } },
  },
}

export default function LandingPage() {
  const navigate = useNavigate()
  const featuresRef = useRef<HTMLDivElement>(null)
  const featuresInView = useInView(featuresRef, { once: true, margin: '-100px' })

  return (
    <div className="min-h-screen bg-[#0f0f1a] text-white overflow-x-hidden">
      {/* ---- NAVBAR ---- */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0f0f1a]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-black text-lg tracking-tight">FUTURE VIP</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
              Sign In
            </Button>
            <Button variant="primary" size="sm" onClick={() => navigate('/register')}>
              Get Started Free
            </Button>
          </div>
        </div>
      </nav>

      {/* ---- HERO ---- */}
      <section className="relative pt-32 pb-24 px-4 sm:px-6 lg:px-8 overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-[120px]" />
          <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-violet-600/20 rounded-full blur-[100px]" />
        </div>

        <div className="max-w-5xl mx-auto text-center relative">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-slate-300 mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            By Unemployed, For Unemployed
          </motion.div>

          {/* H1 */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl sm:text-6xl md:text-7xl font-black leading-tight tracking-tight mb-6"
          >
            Your AI Career Team,
            <br />
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Always On.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            13 specialized AI agents working 24/7 to match you with perfect opportunities, optimize your resume, and ace your interviews.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
          >
            <Button
              variant="primary"
              size="lg"
              rightIcon={<ArrowRight className="w-5 h-5" />}
              onClick={() => navigate('/register')}
              className="text-base px-8"
            >
              Start Free — No Credit Card
            </Button>
            <Button
              variant="ghost"
              size="lg"
              leftIcon={<Play className="w-5 h-5" />}
              onClick={() => navigate('/login')}
              className="text-base"
            >
              Watch Demo
            </Button>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.45 }}
            className="grid grid-cols-3 gap-8 max-w-lg mx-auto border-t border-white/10 pt-10"
          >
            <StatItem value={50} suffix="K+" label="Active Users" />
            <StatItem value={2} suffix="M+" label="Jobs Matched" />
            <StatItem value={94} suffix="%" label="Interview Success" />
          </motion.div>
        </div>
      </section>

      {/* ---- FEATURES ---- */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-transparent to-white/2">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
              Everything Your Job Search Needs
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              One platform. 13 AI agents. From resume to offer letter.
            </p>
          </motion.div>

          <motion.div
            ref={featuresRef}
            initial="initial"
            animate={featuresInView ? 'animate' : 'initial'}
            variants={stagger.container}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          >
            {FEATURES.map((f, i) => (
              <motion.div
                key={i}
                variants={stagger.item}
                className={`p-6 rounded-2xl border bg-gradient-to-br ${f.color} hover:scale-[1.02] transition-transform duration-300`}
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${f.iconColor}`}>
                  {f.icon}
                </div>
                <h3 className="text-base font-bold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ---- HOW IT WORKS ---- */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">How It Works</h2>
            <p className="text-slate-400">Four steps from upload to offer</p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {HOW_IT_WORKS.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative text-center"
              >
                {/* Connector line */}
                {i < HOW_IT_WORKS.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-[calc(50%+2rem)] right-[-2rem] h-px bg-gradient-to-r from-indigo-500/40 to-transparent" />
                )}
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/30 to-violet-500/20 border border-indigo-500/30 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-black text-indigo-400">{step.step}</span>
                </div>
                <h3 className="text-base font-bold text-white mb-2">{step.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ---- TESTIMONIALS ---- */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-white/2">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">Success Stories</h2>
            <p className="text-slate-400">Join thousands who landed their dream roles</p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="glass-card p-6"
              >
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(5)].map((_, si) => (
                    <Star key={si} className="w-4 h-4 fill-amber-400 text-amber-400" />
                  ))}
                  <span className="ml-auto text-xs font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
                    {t.score}% match
                  </span>
                </div>
                <p className="text-sm text-slate-300 italic leading-relaxed mb-4">"{t.text}"</p>
                <div>
                  <p className="text-sm font-semibold text-white">{t.name}</p>
                  <p className="text-xs text-slate-400">{t.role}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ---- TECH STACK ---- */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-slate-500 uppercase tracking-widest mb-8">Powered By</p>
          <div className="flex flex-wrap items-center justify-center gap-6">
            {TECH_STACK.map((t) => (
              <div key={t.name} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-slate-300">
                <span>{t.icon}</span>
                {t.name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---- FINAL CTA ---- */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative p-12 rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-violet-500/5 overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/10 to-violet-600/5 pointer-events-none" />
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
                Start Your AI Career Journey Today
              </h2>
              <p className="text-slate-400 mb-8 leading-relaxed">
                Join 50,000+ job seekers who found their dream role with FUTURE VIP. Free to start. No credit card required.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button
                  variant="primary"
                  size="lg"
                  rightIcon={<ArrowRight className="w-5 h-5" />}
                  onClick={() => navigate('/register')}
                  className="text-base px-8"
                >
                  Create Free Account
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  leftIcon={<Github className="w-5 h-5" />}
                  onClick={() => window.open('https://github.com/writersrinivasan/futureVIP', '_blank')}
                  className="text-base"
                >
                  View on GitHub
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ---- FOOTER ---- */}
      <footer className="border-t border-white/8 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <Zap className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="font-black tracking-tight">FUTURE VIP</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-400">
              <button className="hover:text-white transition-colors" onClick={() => navigate('/login')}>Sign In</button>
              <button className="hover:text-white transition-colors" onClick={() => navigate('/register')}>Register</button>
              <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-white transition-colors">Terms</a>
            </div>
            <p className="text-xs text-slate-600">
              © {new Date().getFullYear()} FUTURE VIP. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
