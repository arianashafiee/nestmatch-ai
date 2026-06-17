import { Trash2 } from 'lucide-react'
import { confirmDeleteListing } from '@/lib/listingActions'
import { cn } from '@/lib/utils'
import type { Apartment } from '@/types/apartment'

interface DeleteListingButtonProps {
  apartment: Apartment
  onDelete: (id: number) => void
  className?: string
  size?: 'sm' | 'md'
}

export function DeleteListingButton({
  apartment,
  onDelete,
  className,
  size = 'md',
}: DeleteListingButtonProps) {
  const iconClass = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'
  const paddingClass = size === 'sm' ? 'p-1.5' : 'p-2'

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!confirmDeleteListing(apartment)) return
        onDelete(apartment.id)
      }}
      className={cn(
        'rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600',
        paddingClass,
        className,
      )}
      aria-label={`Delete ${apartment.title ?? 'listing'}`}
    >
      <Trash2 className={iconClass} />
    </button>
  )
}
