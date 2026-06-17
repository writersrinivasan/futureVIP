import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, Eye, EyeOff, User } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { useAuth } from '@/hooks/useAuth'

const registerSchema = z
  .object({
    full_name: z
      .string()
      .min(2, 'Full name must be at least 2 characters')
      .max(100, 'Full name is too long'),
    email: z.string().email('Please enter a valid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirm_password: z.string(),
    terms: z.boolean().refine((val) => val === true, {
      message: 'You must accept the terms and conditions',
    }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  })

type RegisterFormData = z.infer<typeof registerSchema>

export const RegisterForm = () => {
  const { register: registerUser, isLoading } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  const passwordValue = watch('password', '')

  const getPasswordStrength = (password: string) => {
    let strength = 0
    if (password.length >= 8) strength++
    if (/[A-Z]/.test(password)) strength++
    if (/[0-9]/.test(password)) strength++
    if (/[^A-Za-z0-9]/.test(password)) strength++
    return strength
  }

  const strength = getPasswordStrength(passwordValue)
  const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong']
  const strengthColors = ['', 'bg-danger-500', 'bg-warning-500', 'bg-primary-500', 'bg-success-500']

  const onSubmit = async (data: RegisterFormData) => {
    try {
      await registerUser(data)
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
      className="space-y-4"
    >
      {/* Full Name */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">Full Name</label>
        <div className="relative">
          <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('full_name')}
            type="text"
            placeholder="John Doe"
            className={`input-field pl-10 ${errors.full_name ? 'border-danger-500/50' : ''}`}
          />
        </div>
        {errors.full_name && (
          <p className="text-xs text-danger-400">{errors.full_name.message}</p>
        )}
      </div>

      {/* Email */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">Email Address</label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('email')}
            type="email"
            placeholder="you@example.com"
            className={`input-field pl-10 ${errors.email ? 'border-danger-500/50' : ''}`}
          />
        </div>
        {errors.email && (
          <p className="text-xs text-danger-400">{errors.email.message}</p>
        )}
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">Password</label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('password')}
            type={showPassword ? 'text' : 'password'}
            placeholder="Min 8 chars, 1 uppercase, 1 number"
            className={`input-field pl-10 pr-10 ${errors.password ? 'border-danger-500/50' : ''}`}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {passwordValue && (
          <div className="space-y-1">
            <div className="flex gap-1">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                    strength >= i ? strengthColors[strength] : 'bg-white/10'
                  }`}
                />
              ))}
            </div>
            <p className={`text-xs ${strength >= 3 ? 'text-success-400' : 'text-slate-400'}`}>
              {strengthLabels[strength]}
            </p>
          </div>
        )}
        {errors.password && (
          <p className="text-xs text-danger-400">{errors.password.message}</p>
        )}
      </div>

      {/* Confirm Password */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">Confirm Password</label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            {...register('confirm_password')}
            type={showConfirm ? 'text' : 'password'}
            placeholder="••••••••"
            className={`input-field pl-10 pr-10 ${errors.confirm_password ? 'border-danger-500/50' : ''}`}
          />
          <button
            type="button"
            onClick={() => setShowConfirm(!showConfirm)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
          >
            {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {errors.confirm_password && (
          <p className="text-xs text-danger-400">{errors.confirm_password.message}</p>
        )}
      </div>

      {/* Terms */}
      <div className="space-y-1">
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            {...register('terms')}
            type="checkbox"
            className="mt-0.5 w-4 h-4 rounded border-white/20 bg-white/5 accent-primary-500 cursor-pointer"
          />
          <span className="text-sm text-slate-400">
            I agree to the{' '}
            <a href="#" className="text-primary-400 hover:text-primary-300">Terms of Service</a>{' '}
            and{' '}
            <a href="#" className="text-primary-400 hover:text-primary-300">Privacy Policy</a>
          </span>
        </label>
        {errors.terms && (
          <p className="text-xs text-danger-400">{errors.terms.message}</p>
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
        Create Account
      </Button>

      <p className="text-center text-sm text-slate-400">
        Already have an account?{' '}
        <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
          Sign in
        </Link>
      </p>
    </motion.form>
  )
}
