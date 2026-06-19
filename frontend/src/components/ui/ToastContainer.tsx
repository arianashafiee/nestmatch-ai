import { X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '@/context/ToastContext'
import { cn } from '@/lib/utils'

const variants = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-slate-200 bg-white text-slate-800',
}

export function ToastContainer() {
  const { toasts, dismissToast } = useToast()
  const navigate = useNavigate()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex max-w-sm flex-col gap-2">
      {toasts.map((toast) => {
        const isClickable = Boolean(toast.href)

        const handleOpen = () => {
          if (!toast.href) return
          dismissToast(toast.id)
          navigate(toast.href)
        }

        return (
          <div
            key={toast.id}
            role={isClickable ? 'button' : undefined}
            tabIndex={isClickable ? 0 : undefined}
            onClick={isClickable ? handleOpen : undefined}
            onKeyDown={
              isClickable
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      handleOpen()
                    }
                  }
                : undefined
            }
            className={cn(
              'flex items-start gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg',
              variants[toast.variant],
              isClickable &&
                'cursor-pointer transition-shadow hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-indigo-400',
            )}
          >
            <p className="flex-1">
              {toast.message}
              {isClickable && (
                <span className="mt-1 block text-xs font-medium opacity-80">
                  Tap to view listing
                </span>
              )}
            </p>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                dismissToast(toast.id)
              }}
              className="shrink-0 opacity-60 hover:opacity-100"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
