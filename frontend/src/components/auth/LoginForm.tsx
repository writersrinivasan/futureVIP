import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { useAuth } from '@/hooks/useAuth'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

type LoginFormData = z.infer<typeof loginSchema>

export const LoginForm = () => {
  const { login, isLoading } = useAuth()
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data)
    } catch {
      // Error handled in useAuth
    }
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5"
    >
      {/* Email */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">Email Address</label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('email')}
            type="email"
            placeholder="you@example.com"
            className={`input-field pl-10 ${errors.email ? 'border-danger-500/50 focus:ring-danger-500/50' : ''}`}
          />
        </div>
        {errors.email && (
          <p className="text-xs text-danger-400">{errors.email.message}</p>
        )}
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium text-slate-300">Password</label>
          <Link
            to="/forgot-password"
            className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
          >
            Forgot password?
          </Link>
        </div>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('password')}
            type={showPassword ? 'text' : 'password'}
            placeholder="••••••••"
            className={`input-field pl-10 pr-10 ${errors.password ? 'border-danger-500/50 focus:ring-danger-500/50' : ''}`}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {errors.password && (
          <p className="text-xs text-danger-400">{errors.password.message}</p>
        )}
      </div>

      {/* Submit */}
      <Button
        type="submit"
        variant="primary"
        fullWidth
        size="lg"
        isLoading={isLoading}
      >
        Sign In
      </Button>

      <p className="text-center text-sm text-slate-400">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
          Create one free
        </Link>
      </p>
    </motion.form>
  )
}
