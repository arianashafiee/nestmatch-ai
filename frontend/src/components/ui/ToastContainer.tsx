import { X } from 'lucide-react'
import { useToast } from '@/context/ToastContext'
import { cn } from '@/lib/utils'

const variants = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-slate-200 bg-white text-slate-800',
}

export function ToastContainer() {
  const { toasts, dismissToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex max-w-sm flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'flex items-start gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg',
            variants[toast.variant],
          )}
        >
          <p className="flex-1">{toast.message}</p>
          <button
            type="button"
            onClick={() => dismissToast(toast.id)}
            className="shrink-0 opacity-60 hover:opacity-100"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
