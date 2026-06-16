import { cn } from '@/lib/utils'

interface TagToggleProps {
  label: string
  selected: boolean
  onToggle: () => void
  variant?: 'must-have' | 'dealbreaker'
}

export function TagToggle({
  label,
  selected,
  onToggle,
  variant = 'must-have',
}: TagToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'rounded-full border px-3 py-1.5 text-sm font-medium transition-colors',
        selected
          ? variant === 'must-have'
            ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
            : 'border-red-400 bg-red-50 text-red-700'
          : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
      )}
    >
      {label}
    </button>
  )
}
