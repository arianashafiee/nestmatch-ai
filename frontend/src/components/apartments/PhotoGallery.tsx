import { useState } from 'react'
import { ChevronLeft, ChevronRight, ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { photoProxyUrl } from '@/types/apartment'

interface PhotoGalleryProps {
  photos: string[]
  title?: string
  className?: string
}

export function PhotoGallery({ photos = [], title, className }: PhotoGalleryProps) {
  const safePhotos = Array.isArray(photos) ? photos : []
  const [index, setIndex] = useState(0)

  if (!safePhotos.length) {
    return (
      <div
        className={cn(
          'flex h-56 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-slate-500',
          className,
        )}
      >
        <ImageIcon className="h-10 w-10 text-slate-300" />
        <p className="mt-2 text-sm">No photos available yet</p>
        <p className="text-xs text-slate-400">
          Paste a listing URL and we will pull photos from the page
        </p>
      </div>
    )
  }

  const current = safePhotos[index]
  const proxied = photoProxyUrl(current)

  return (
    <div className={cn('overflow-hidden rounded-xl border border-slate-200 bg-white', className)}>
      <div className="relative aspect-[16/10] bg-slate-100">
        <img
          src={proxied}
          alt={title ? `${title} photo ${index + 1}` : `Listing photo ${index + 1}`}
          className="h-full w-full object-cover"
          loading={index === 0 ? 'eager' : 'lazy'}
          decoding="async"
          onError={(e) => {
            const img = e.currentTarget
            if (img.src !== current) {
              img.src = current
            }
          }}
        />
        {safePhotos.length > 1 && (
          <>
            <button
              type="button"
              onClick={() => setIndex((i) => (i === 0 ? safePhotos.length - 1 : i - 1))}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
              aria-label="Previous photo"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setIndex((i) => (i === safePhotos.length - 1 ? 0 : i + 1))}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
              aria-label="Next photo"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
            <span className="absolute bottom-2 right-2 rounded-full bg-black/50 px-2.5 py-1 text-xs text-white">
              {index + 1} / {safePhotos.length}
            </span>
          </>
        )}
      </div>
      {safePhotos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto border-t border-slate-100 p-3">
          {safePhotos.map((photo, i) => (
            <button
              key={photo}
              type="button"
              onClick={() => setIndex(i)}
              className={cn(
                'h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2',
                i === index ? 'border-indigo-500' : 'border-transparent opacity-70 hover:opacity-100',
              )}
            >
              <img
                src={photoProxyUrl(photo)}
                alt=""
                className="h-full w-full object-cover"
                onError={(e) => {
                  e.currentTarget.src = photo
                }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
