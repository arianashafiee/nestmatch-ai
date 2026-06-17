import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { ScoreBadge } from '@/components/apartments/ScoreBadge'
import { useApartmentCommute } from '@/context/CommuteContext'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { formatCommuteToCampus } from '@/lib/commute'
import { cn } from '@/lib/utils'
import {
  SCORE_CATEGORIES,
  type Apartment,
  type ListingAnalysis,
} from '@/types/apartment'

interface AnalysisDashboardProps {
  apartment: Apartment
  showRawText?: boolean
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            value >= 80
              ? 'bg-emerald-500'
              : value >= 60
                ? 'bg-indigo-500'
                : value >= 40
                  ? 'bg-amber-500'
                  : 'bg-red-500',
          )}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}

function AnalysisContent({
  analysis,
  apartmentId,
}: {
  analysis: ListingAnalysis
  apartmentId: number
}) {
  const { profile } = useStudentProfile()
  const commute = useApartmentCommute(apartmentId)
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            {analysis.title}
          </h2>
          <p className="mt-1 text-slate-600">{analysis.location}</p>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-500">
            {analysis.rent_monthly != null && (
              <span className="font-medium text-indigo-600">
                ${analysis.rent_monthly.toLocaleString()}/mo
              </span>
            )}
            {analysis.bedrooms != null && (
              <span>
                {analysis.bedrooms === 0
                  ? 'Studio'
                  : `${analysis.bedrooms} bed`}
              </span>
            )}
            {analysis.bathrooms != null && (
              <span>{analysis.bathrooms} bath</span>
            )}
            {commute != null ? (
              <span>{formatCommuteToCampus(commute.minutes, profile.commuteMode)}</span>
            ) : analysis.estimated_commute_minutes != null ? (
              <span>{analysis.estimated_commute_minutes} min commute</span>
            ) : null}
          </div>
        </div>
        <ScoreBadge score={analysis.compatibility_score} size="lg" />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Sparkles className="h-4 w-4 text-indigo-600" />
          Compatibility Breakdown
        </h3>
        <div className="mt-4 space-y-3">
          {SCORE_CATEGORIES.map(({ key, label }) => (
            <ScoreBar
              key={key}
              label={label}
              value={analysis.score_breakdown[key]}
            />
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
            <CheckCircle2 className="h-4 w-4" />
            Pros
          </h3>
          <ul className="mt-3 space-y-2">
            {analysis.pros.map((pro) => (
              <li key={pro} className="text-sm text-emerald-900">
                • {pro}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50/50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-red-800">
            <XCircle className="h-4 w-4" />
            Cons
          </h3>
          <ul className="mt-3 space-y-2">
            {analysis.cons.map((con) => (
              <li key={con} className="text-sm text-red-900">
                • {con}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {analysis.red_flags.length > 0 && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-red-800">
            <AlertTriangle className="h-4 w-4" />
            Red Flags
          </h3>
          <ul className="mt-3 space-y-2">
            {analysis.red_flags.map((flag) => (
              <li key={flag} className="text-sm text-red-900">
                • {flag}
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.missing_info.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800">
            <HelpCircle className="h-4 w-4" />
            Missing Info
          </h3>
          <ul className="mt-3 space-y-2">
            {analysis.missing_info.map((info) => (
              <li key={info} className="text-sm text-amber-900">
                • {info}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
        <h3 className="text-sm font-semibold text-indigo-900">
          Questions to Ask the Landlord
        </h3>
        <ol className="mt-3 list-decimal space-y-2 pl-4">
          {analysis.follow_up_questions.map((q) => (
            <li key={q} className="text-sm text-indigo-900">
              {q}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

export function AnalysisDashboard({
  apartment,
  showRawText,
}: AnalysisDashboardProps) {
  if (!apartment.analysis) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
        AI analysis not available yet.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <AnalysisContent analysis={apartment.analysis} apartmentId={apartment.id} />
      {showRawText && (
        <details className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <summary className="cursor-pointer text-sm font-medium text-slate-700">
            Original listing text
          </summary>
          <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-600">
            {apartment.rawText}
          </pre>
        </details>
      )}
    </div>
  )
}
