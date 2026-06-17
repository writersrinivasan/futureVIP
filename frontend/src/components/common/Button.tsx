import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 hover:bg-primary-500 text-white border border-transparent shadow-lg shadow-primary-900/30',
  secondary:
    'bg-secondary-600 hover:bg-secondary-500 text-white border border-transparent shadow-lg shadow-secondary-900/30',
  outline:
    'bg-transparent hover:bg-primary-500/10 text-primary-400 border border-primary-500/50 hover:border-primary-400',
  ghost:
    'bg-transparent hover:bg-white/5 text-slate-300 hover:text-white border border-transparent',
  danger:
    'bg-danger-600 hover:bg-danger-500 text-white border border-transparent shadow-lg shadow-danger-900/30',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2.5 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading

    return (
      <motion.button
        ref={ref}
        whileTap={{ scale: isDisabled ? 1 : 0.97 }}
        className={cn(
          'inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:ring-offset-2 focus:ring-offset-transparent',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        disabled={isDisabled}
        {...(props as React.ComponentProps<typeof motion.button>)}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
        )}
        {children}
        {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
      </motion.button>
    )
  }
)

Button.displayName = 'Button'
