import { cn } from '@/lib/utils'
import { scoreBg, scoreColor } from '@/types/apartment'

interface ScoreBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: 'h-10 w-10 text-sm',
  md: 'h-14 w-14 text-lg',
  lg: 'h-20 w-20 text-2xl',
}

export function ScoreBadge({ score, size = 'md', className }: ScoreBadgeProps) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full border-2 font-bold',
        sizes[size],
        scoreBg(score),
        scoreColor(score),
        className,
      )}
    >
      {score}
    </div>
  )
}
