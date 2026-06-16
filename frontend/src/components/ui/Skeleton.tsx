import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded-lg bg-slate-200/80', className)}
    />
  )
}

export function ApartmentCardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-3 w-full" />
        </div>
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>
      <div className="mt-4 grid grid-cols-5 gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8" />
        ))}
      </div>
    </div>
  )
}
