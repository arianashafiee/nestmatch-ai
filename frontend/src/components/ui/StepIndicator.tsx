import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StepIndicatorProps {
  steps: string[]
  currentStep: number
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      {steps.map((step, index) => {
        const isComplete = index < currentStep
        const isCurrent = index === currentStep

        return (
          <div key={step} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold',
                  isComplete && 'bg-indigo-600 text-white',
                  isCurrent && 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-600',
                  !isComplete && !isCurrent && 'bg-slate-100 text-slate-400',
                )}
              >
                {isComplete ? <Check className="h-4 w-4" /> : index + 1}
              </div>
              <span
                className={cn(
                  'hidden text-sm sm:inline',
                  isCurrent ? 'font-medium text-slate-900' : 'text-slate-500',
                )}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'hidden h-px w-8 sm:block',
                  index < currentStep ? 'bg-indigo-300' : 'bg-slate-200',
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
