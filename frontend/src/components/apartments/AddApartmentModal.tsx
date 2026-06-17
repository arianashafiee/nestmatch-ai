import { useEffect, useState } from 'react'
import { Link2, Loader2, Search, Sparkles, X } from 'lucide-react'
import { DiscoverListings } from '@/components/apartments/DiscoverListings'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { useApartments } from '@/context/ApartmentsContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { cn } from '@/lib/utils'

const MIN_TEXT_LENGTH = 10

type Tab = 'discover' | 'paste'

export function AddApartmentModal() {
  const {
    isAddModalOpen,
    closeAddModal,
    addApartment,
    isSubmitting,
    submitError,
    isListingSearchInProgress,
    listingSearch,
  } = useApartments()
  const { isProfileComplete } = useStudentProfile()

  const [tab, setTab] = useState<Tab>('discover')
  const [rawText, setRawText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    if (!isAddModalOpen) {
      setTab('discover')
      setRawText('')
      setError(null)
      setSubmitted(false)
    }
  }, [isAddModalOpen])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeAddModal()
    }
    if (isAddModalOpen) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isAddModalOpen, closeAddModal])

  if (!isAddModalOpen) return null

  const handleSubmit = async () => {
    if (rawText.trim().length < MIN_TEXT_LENGTH) {
      setError(`Paste at least ${MIN_TEXT_LENGTH} characters of listing text or a URL.`)
      return
    }
    setError(null)
    await addApartment(rawText)
    setSubmitted(true)
    setTimeout(() => closeAddModal(), 1500)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={closeAddModal}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-apartment-title"
        className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col rounded-t-2xl border border-slate-200 bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-100 p-2 text-indigo-600">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="add-apartment-title"
                className="text-lg font-semibold text-slate-900"
              >
                Find Apartments
              </h2>
              <p className="text-sm text-slate-500">
                {isListingSearchInProgress
                  ? 'Search running in the background — close anytime and reopen to view results'
                  : listingSearch?.results.length
                    ? `${listingSearch.results.length} saved listings — search near campus or add a link`
                    : 'Search near campus or add a listing you found'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={closeAddModal}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex border-b border-slate-200 px-5">
          <button
            type="button"
            onClick={() => setTab('discover')}
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              tab === 'discover'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-700',
            )}
          >
            <Search className="h-4 w-4" />
            Search near campus
          </button>
          <button
            type="button"
            onClick={() => setTab('paste')}
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              tab === 'paste'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-700',
            )}
          >
            <Link2 className="h-4 w-4" />
            Paste a listing
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {!isProfileComplete && (
            <div className="mb-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Complete your{' '}
              <a href="/profile" className="font-medium underline">
                student profile
              </a>{' '}
              so NestMatch can search and score listings for your campus and budget.
            </div>
          )}

          {tab === 'discover' ? (
            <DiscoverListings onAdded={() => {
              setSubmitted(true)
              setTimeout(() => closeAddModal(), 1200)
            }} />
          ) : (
            <>
              <p className="mb-4 text-sm text-slate-600">
                Paste a listing URL from JHU Off-Campus Housing, Apartments.com, Rent.com,
                Craigslist, Zillow, or copy the description. NestMatch will pull <strong>all photos</strong>{' '}
                from the page automatically.
              </p>
              <Textarea
                id="listing-input"
                label="Listing text or URL"
                placeholder={`Paste an apartment listing URL or copy the full listing description here...\n\nExample:\nhttps://example.com/listing/123\n\n2BR / 1BA — $1,200/mo\nNear campus, in-unit laundry, parking included...`}
                value={rawText}
                onChange={(e) => {
                  setRawText(e.target.value)
                  setError(null)
                }}
                rows={12}
                className="min-h-[240px] font-mono text-sm"
                error={error ?? undefined}
              />
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <Link2 className="h-3.5 w-3.5" />
                URLs are auto-detected from pasted text
              </div>
            </>
          )}

          {submitError && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {submitError}
            </p>
          )}

          {submitted && (
            <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              Listing saved — AI analysis in progress. Check your board for the
              compatibility score.
            </p>
          )}
        </div>

        {tab === 'paste' && (
          <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
            <span
              className={cn(
                'text-xs',
                rawText.length >= MIN_TEXT_LENGTH
                  ? 'text-emerald-600'
                  : 'text-slate-400',
              )}
            >
              {rawText.length} characters
            </span>
            <div className="flex gap-2">
              <Button variant="outline" onClick={closeAddModal}>
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting || submitted}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Listing'
                )}
              </Button>
            </div>
          </div>
        )}

        {tab === 'discover' && (
          <div className="flex justify-end border-t border-slate-200 px-5 py-4">
            <Button variant="outline" onClick={closeAddModal}>
              Close
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
