import { type ReactNode } from 'react'
import * as RadixTooltip from '@radix-ui/react-tooltip'
import { cn } from '@/utils/cn'

interface TooltipProps {
  children: ReactNode
  content: ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  delayDuration?: number
  className?: string
}

export const TooltipProvider = RadixTooltip.Provider

export const Tooltip = ({
  children,
  content,
  side = 'top',
  delayDuration = 300,
  className,
}: TooltipProps) => {
  return (
    <RadixTooltip.Root delayDuration={delayDuration}>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={8}
          className={cn(
            'bg-dark-card border border-white/10 text-slate-200 text-xs px-2.5 py-1.5',
            'rounded-lg shadow-xl backdrop-blur-md z-50 max-w-xs',
            'animate-fade-in',
            className
          )}
        >
          {content}
          <RadixTooltip.Arrow className="fill-dark-card" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  )
}
