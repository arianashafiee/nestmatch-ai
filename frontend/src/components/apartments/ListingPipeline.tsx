import { useEffect, useMemo, useState } from 'react'
import { CalendarClock, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import {
  KANBAN_COLUMNS,
  canAdvanceToMilestone,
  isMilestoneComplete,
  type PipelineMilestone,
} from '@/lib/kanban'
import {
  combineTourDateTime,
  formatTourDateTime,
  splitTourDateTime,
} from '@/lib/tours'
import { cn } from '@/lib/utils'
import type { Apartment, ApartmentStatus } from '@/types/apartment'

const PIPELINE_STEPS: PipelineMilestone[] = [
  'contacted',
  'tour_scheduled',
  'applied',
]

interface ListingPipelineProps {
  apartment: Apartment
  onUpdate: (updates: {
    status?: ApartmentStatus
    tourAt?: string | null
  }) => Promise<void>
  isSaving?: boolean
  className?: string
}

export function ListingPipeline({
  apartment,
  onUpdate,
  isSaving = false,
  className,
}: ListingPipelineProps) {
  const { status } = apartment
  const archived = status === 'archived'
  const initialSplit = useMemo(
    () => splitTourDateTime(apartment.tourAt),
    [apartment.tourAt],
  )
  const [tourDate, setTourDate] = useState(initialSplit.date)
  const [tourTime, setTourTime] = useState(initialSplit.time)
  const [scheduleError, setScheduleError] = useState<string | null>(null)

  useEffect(() => {
    const split = splitTourDateTime(apartment.tourAt)
    setTourDate(split.date)
    setTourTime(split.time)
  }, [apartment.tourAt])

  const handleMarkContacted = async () => {
    await onUpdate({ status: 'contacted' })
  }

  const handleScheduleTour = async () => {
    const tourAt = combineTourDateTime(tourDate, tourTime)
    if (!tourAt) {
      setScheduleError('Pick a date and time for your tour.')
      return
    }
    if (new Date(tourAt).getTime() <= Date.now()) {
      setScheduleError('Tour time must be in the future.')
      return
    }
    setScheduleError(null)
    await onUpdate({ status: 'tour_scheduled', tourAt })
  }

  const handleRescheduleTour = async () => {
    const tourAt = combineTourDateTime(tourDate, tourTime)
    if (!tourAt) {
      setScheduleError('Pick a date and time for your tour.')
      return
    }
    setScheduleError(null)
    await onUpdate({ tourAt })
  }

  const handleMarkApplied = async () => {
    await onUpdate({ status: 'applied' })
  }

  const handleArchiveToggle = async (checked: boolean) => {
    await onUpdate({ status: checked ? 'archived' : 'interested' })
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
        Complete each step in order — contacted, then schedule a tour, then
        apply.
      </p>

      <ol className="mt-4 space-y-0">
        {PIPELINE_STEPS.map((milestone, index) => {
          const column = KANBAN_COLUMNS.find((c) => c.key === milestone)
          const complete = isMilestoneComplete(status, milestone)
          const actionable = canAdvanceToMilestone(status, milestone)
          const isTourStep = milestone === 'tour_scheduled'
          const showTourForm =
            isTourStep &&
            (actionable || (complete && Boolean(apartment.tourAt)))

          return (
            <li key={milestone} className="relative flex gap-3 pb-4 last:pb-0">
              {index < PIPELINE_STEPS.length - 1 && (
                <span
                  className={cn(
                    'absolute left-[15px] top-8 h-[calc(100%-12px)] w-0.5',
                    complete ? 'bg-indigo-300' : 'bg-slate-200',
                  )}
                  aria-hidden
                />
              )}

              <div
                className={cn(
                  'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold',
                  complete
                    ? 'border-indigo-600 bg-indigo-600 text-white'
                    : actionable
                      ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 bg-white text-slate-400',
                )}
              >
                {complete ? <Check className="h-4 w-4" /> : index + 1}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p
                    className={cn(
                      'text-sm font-medium',
                      complete ? 'text-indigo-900' : 'text-slate-900',
                    )}
                  >
                    {column?.label ?? milestone}
                  </p>
                  {complete && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                      Done
                    </span>
                  )}
                </div>
                {column?.description && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    {column.description}
                  </p>
                )}

                {milestone === 'contacted' && actionable && (
                  <Button
                    size="sm"
                    className="mt-3"
                    onClick={handleMarkContacted}
                    disabled={isSaving || archived}
                  >
                    {isSaving ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Mark as contacted
                  </Button>
                )}

                {showTourForm && (
                  <div className="mt-3 space-y-3 rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
                    {complete && apartment.tourAt && status !== 'contacted' && (
                      <p className="flex items-center gap-2 text-sm font-medium text-indigo-900">
                        <CalendarClock className="h-4 w-4 shrink-0" />
                        {formatTourDateTime(apartment.tourAt)}
                      </p>
                    )}
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input
                        id={`tour-date-${apartment.id}`}
                        label="Tour date"
                        type="date"
                        value={tourDate}
                        onChange={(e) => {
                          setTourDate(e.target.value)
                          setScheduleError(null)
                        }}
                        disabled={
                          isSaving || archived || (!actionable && !complete)
                        }
                      />
                      <Input
                        id={`tour-time-${apartment.id}`}
                        label="Tour time"
                        type="time"
                        value={tourTime}
                        onChange={(e) => {
                          setTourTime(e.target.value)
                          setScheduleError(null)
                        }}
                        disabled={
                          isSaving || archived || (!actionable && !complete)
                        }
                      />
                    </div>
                    {scheduleError && (
                      <p className="text-xs text-red-600">{scheduleError}</p>
                    )}
                    {actionable ? (
                      <Button
                        size="sm"
                        onClick={handleScheduleTour}
                        disabled={isSaving || archived}
                      >
                        {isSaving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CalendarClock className="h-4 w-4" />
                        )}
                        Schedule tour
                      </Button>
                    ) : complete && apartment.tourAt ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleRescheduleTour}
                        disabled={isSaving || archived}
                      >
                        Update tour time
                      </Button>
                    ) : null}
                  </div>
                )}

                {milestone === 'applied' && actionable && (
                  <Button
                    size="sm"
                    className="mt-3"
                    onClick={handleMarkApplied}
                    disabled={isSaving || archived}
                  >
                    {isSaving ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Mark as applied
                  </Button>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      <div className="mt-4 border-t border-slate-100 pt-4">
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
            disabled={isSaving}
            onChange={(e) => handleArchiveToggle(e.target.checked)}
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
      </div>
    </div>
  )
}
