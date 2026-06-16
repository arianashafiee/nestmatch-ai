import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'outline'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300',
  secondary:
    'bg-slate-100 text-slate-900 hover:bg-slate-200 disabled:bg-slate-50',
  ghost: 'text-slate-700 hover:bg-slate-100',
  outline:
    'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  lg: 'h-11 px-6 text-sm',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
