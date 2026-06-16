import { BarChart3 } from 'lucide-react'

export function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
        <BarChart3 className="mx-auto h-10 w-10 text-slate-400" />
        <h2 className="mt-4 text-lg font-semibold text-slate-900">Analytics</h2>
        <p className="mt-2 text-sm text-slate-500">
          Hunt insights and score trends will appear here in a future phase.
        </p>
      </div>
    </div>
  )
}
