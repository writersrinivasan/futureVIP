import * as RadixSelect from '@radix-ui/react-select'
import { ChevronDown, Check } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { SelectOption } from '@/types'

interface SelectProps {
  value?: string
  onValueChange?: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  className?: string
  label?: string
}

export const Select = ({
  value,
  onValueChange,
  options,
  placeholder = 'Select an option',
  disabled = false,
  className,
  label,
}: SelectProps) => {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-sm font-medium text-slate-300">{label}</label>}
      <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
        <RadixSelect.Trigger
          className={cn(
            'flex items-center justify-between w-full px-3 py-2.5 text-sm',
            'bg-white/5 border border-white/10 rounded-lg text-slate-100',
            'hover:bg-white/8 hover:border-white/20 transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-primary-500/50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'data-[placeholder]:text-slate-500',
            className
          )}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>

        <RadixSelect.Portal>
          <RadixSelect.Content
            className={cn(
              'bg-dark-card border border-white/10 rounded-xl shadow-xl z-50',
              'overflow-hidden backdrop-blur-md',
              'data-[side=bottom]:animate-slide-down data-[side=top]:animate-slide-up'
            )}
            position="popper"
            sideOffset={4}
          >
            <RadixSelect.Viewport className="p-1">
              {options.map((option) => (
                <RadixSelect.Item
                  key={option.value}
                  value={option.value}
                  className={cn(
                    'flex items-center justify-between px-3 py-2 text-sm rounded-lg',
                    'text-slate-300 hover:text-white hover:bg-white/10',
                    'cursor-pointer focus:outline-none focus:bg-white/10',
                    'data-[highlighted]:bg-primary-600/20 data-[highlighted]:text-white',
                    'data-[state=checked]:text-primary-300 data-[state=checked]:bg-primary-600/10'
                  )}
                >
                  <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <Check className="w-4 h-4 text-primary-400" />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  )
}
