import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/cn'

interface CardProps {
  children: ReactNode
  className?: string
  header?: ReactNode
  footer?: ReactNode
  hover?: boolean
  glass?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
  onClick?: () => void
}

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-5',
  lg: 'p-6',
}

export const Card = ({
  children,
  className,
  header,
  footer,
  hover = false,
  glass = true,
  padding = 'md',
  onClick,
}: CardProps) => {
  const Wrapper = hover ? motion.div : 'div'
  const motionProps = hover
    ? {
        whileHover: { scale: 1.01, y: -2 },
        transition: { type: 'spring', stiffness: 400, damping: 25 },
      }
    : {}

  return (
    <Wrapper
      {...motionProps}
      className={cn(
        'rounded-xl border transition-all duration-300',
        glass
          ? 'bg-white/5 backdrop-blur-sm border-white/10'
          : 'bg-dark-card border-dark-border',
        hover && 'cursor-pointer hover:bg-white/8 hover:border-white/20',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {header && (
        <div className="px-5 py-4 border-b border-white/10">
          {header}
        </div>
      )}
      <div className={paddingStyles[padding]}>{children}</div>
      {footer && (
        <div className="px-5 py-4 border-t border-white/10 bg-white/2">
          {footer}
        </div>
      )}
    </Wrapper>
  )
}
