import { cn } from '@/lib/utils'
import {
  KANBAN_COLUMNS,
  isMilestoneComplete,
  milestoneForStatus,
  type PipelineMilestone,
} from '@/lib/kanban'
import type { ApartmentStatus } from '@/types/apartment'

const PROGRESS_MILESTONES: PipelineMilestone[] = [
  'contacted',
  'tour_scheduled',
  'applied',
]

interface ListingProgressChecklistProps {
  status: ApartmentStatus
  onStatusChange: (status: ApartmentStatus) => void
  className?: string
}

export function ListingProgressChecklist({
  status,
  onStatusChange,
  className,
}: ListingProgressChecklistProps) {
  const archived = status === 'archived'

  const handleToggle = (milestone: PipelineMilestone, checked: boolean) => {
    if (checked) {
      onStatusChange(milestone)
      return
    }
    onStatusChange(milestoneForStatus(milestone, false))
  }

  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-4',
        className,
      )}
    >
      <p className="text-sm font-semibold text-slate-900">Your progress</p>
      <p className="mt-1 text-xs text-slate-500">
        Check off steps as you move forward — or drag the card on the board.
      </p>

      <ul className="mt-4 space-y-3">
        {PROGRESS_MILESTONES.map((milestone) => {
          const column = KANBAN_COLUMNS.find((c) => c.key === milestone)
          const checked = isMilestoneComplete(status, milestone)
          const disabled = archived && !checked

          return (
            <li key={milestone}>
              <label
                className={cn(
                  'flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors',
                  checked
                    ? 'border-indigo-200 bg-indigo-50'
                    : 'border-slate-200 bg-slate-50 hover:bg-white',
                  disabled && 'cursor-not-allowed opacity-60',
                )}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  checked={checked}
                  disabled={disabled}
                  onChange={(e) => handleToggle(milestone, e.target.checked)}
                />
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-slate-900">
                    {column?.label ?? milestone}
                  </span>
                  {column?.description && (
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {column.description}
                    </span>
                  )}
                </span>
              </label>
            </li>
          )
        })}

        <li>
          <label
            className={cn(
              'flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors',
              archived
                ? 'border-slate-300 bg-slate-100'
                : 'border-slate-200 bg-slate-50 hover:bg-white',
            )}
          >
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-600 focus:ring-slate-500"
              checked={archived}
              onChange={(e) =>
                onStatusChange(e.target.checked ? 'archived' : 'interested')
              }
            />
            <span className="min-w-0">
              <span className="block text-sm font-medium text-slate-900">
                Archived / ruled out
              </span>
              <span className="mt-0.5 block text-xs text-slate-500">
                Ruled out or no longer considering
              </span>
            </span>
          </label>
        </li>
      </ul>
    </div>
  )
}
