import { useState } from 'react'
import { Loader2, NotebookPen } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { createTourNote, formatTourDateTime, isTourPast } from '@/lib/tours'
import { cn } from '@/lib/utils'
import type { Apartment, TourNote } from '@/types/apartment'

interface ListingTourNotesProps {
  apartment: Apartment
  onSaveNotes: (notes: TourNote[]) => Promise<void>
  isSaving?: boolean
  className?: string
}

export function ListingTourNotes({
  apartment,
  onSaveNotes,
  isSaving = false,
  className,
}: ListingTourNotesProps) {
  const [draft, setDraft] = useState('')
  const canAddNotes =
    apartment.status === 'tour_scheduled' ||
    apartment.status === 'applied' ||
    Boolean(apartment.tourAt)

  if (!canAddNotes) return null

  const tourIsPast = apartment.tourAt ? isTourPast(apartment.tourAt) : false

  const handleAddNote = async () => {
    const text = draft.trim()
    if (!text) return
    const next = [...apartment.tourNotes, createTourNote(text)]
    await onSaveNotes(next)
    setDraft('')
  }

  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-4',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <NotebookPen className="h-5 w-5 text-indigo-600" />
        <div>
          <h3 className="font-semibold text-slate-900">Tour notes</h3>
          <p className="text-xs text-slate-500">
            {tourIsPast
              ? 'Capture impressions after your visit.'
              : 'Jot down questions and things to check during your tour.'}
          </p>
        </div>
      </div>

      {apartment.tourNotes.length > 0 && (
        <ul className="mt-4 space-y-3">
          {apartment.tourNotes.map((note) => (
            <li
              key={note.id}
              className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5"
            >
              <p className="text-sm text-slate-800 whitespace-pre-wrap">
                {note.text}
              </p>
              <p className="mt-1 text-[10px] text-slate-400">
                {formatTourDateTime(note.createdAt)}
              </p>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 space-y-3">
        <Textarea
          id={`tour-notes-${apartment.id}`}
          label="Add a note"
          placeholder="e.g. Unit #2 smelled musty in the basement. Ask about parking pass cost."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={4}
        />
        <Button
          size="sm"
          onClick={handleAddNote}
          disabled={isSaving || !draft.trim()}
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <NotebookPen className="h-4 w-4" />
          )}
          Save note
        </Button>
      </div>
    </div>
  )
}
