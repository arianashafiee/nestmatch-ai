import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  ExternalLink,
  Key,
  Map,
  Search,
  Sparkles,
  XCircle,
} from 'lucide-react'
import { fetchAppConfig, type AppConfig } from '@/lib/api'

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={
        ok
          ? 'inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700'
          : 'inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600'
      }
    >
      {ok ? (
        <CheckCircle2 className="h-3.5 w-3.5" />
      ) : (
        <XCircle className="h-3.5 w-3.5" />
      )}
      {label}
    </span>
  )
}

export function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAppConfig()
      .then(setConfig)
      .catch(() => setError('Could not reach the backend. Start the API on port 8000.'))
  }, [])

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-600">
          API keys are optional. Apartment search works without any keys.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {config && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-slate-900">Current status</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge
              ok={config.database === 'connected'}
              label={`Database ${config.database}`}
            />
            <StatusBadge
              ok={config.aiMode === 'openai'}
              label={
                config.aiMode === 'openai'
                  ? 'AI parsing (OpenAI)'
                  : 'AI parsing (mock — no OpenAI key)'
              }
            />
            <StatusBadge
              ok={config.mapboxConfigured}
              label={
                config.mapboxConfigured
                  ? 'Mapbox maps enabled'
                  : 'Mapbox not configured'
              }
            />
            <StatusBadge ok label="Apartment search (no API key)" />
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start gap-3">
          <Search className="mt-0.5 h-5 w-5 text-indigo-600" />
          <div>
            <h2 className="font-semibold text-slate-900">
              Finding apartments — no API key needed
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              NestMatch searches public listing pages on apartments.com, Rent.com,
              Zillow, Craigslist, and Realtor.com. There is no official Apartments.com
              API — we fetch and parse public HTML. Results can vary if a site
              blocks automated requests.
            </p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              <strong>Best results:</strong> paste a direct{' '}
              <strong>apartments.com</strong> URL when adding a listing. That
              pulls photos, description, and landlord phone/email when the page
              exposes them.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-0.5 h-5 w-5 text-indigo-600" />
          <div className="flex-1">
            <h2 className="font-semibold text-slate-900">
              OpenAI (optional) — smarter AI scores
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Without a key, the app uses a built-in mock parser. With{' '}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                OPENAI_API_KEY
              </code>
              , listing analysis uses GPT for richer pros/cons and follow-up
              questions.
            </p>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-600">
              <li>
                Create a key at{' '}
                <a
                  href="https://platform.openai.com/api-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
                >
                  platform.openai.com
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                Add to{' '}
                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                  nestmatch-ai/backend/.env
                </code>
                :
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                  OPENAI_API_KEY=sk-...
                </pre>
              </li>
              <li>Restart the backend server.</li>
            </ol>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start gap-3">
          <Map className="mt-0.5 h-5 w-5 text-indigo-600" />
          <div className="flex-1">
            <h2 className="font-semibold text-slate-900">
              Mapbox (optional) — live maps on listing pages
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Maps are configured on the <strong>backend</strong>, not in this
              browser UI. Add a public access token (starts with{' '}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                pk.
              </code>
              ) to your backend environment.
            </p>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-600">
              <li>
                Sign up and create a token at{' '}
                <a
                  href="https://account.mapbox.com/access-tokens/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
                >
                  account.mapbox.com
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
              <li>
                Copy{' '}
                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                  backend/.env.example
                </code>{' '}
                to{' '}
                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                  backend/.env
                </code>{' '}
                if you have not already.
              </li>
              <li>
                Add:
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
{`MAPBOX_ACCESS_TOKEN=pk.eyJ1...
MAPBOX_STYLE_URL=mapbox://styles/mapbox/streets-v12`}
                </pre>
              </li>
              <li>Restart the backend — listing detail pages will show an interactive map.</li>
            </ol>
            {config?.mapboxConfigured && (
              <p className="mt-3 text-sm font-medium text-emerald-700">
                Mapbox token detected. Maps are active.
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start gap-3">
          <Key className="mt-0.5 h-5 w-5 text-indigo-600" />
          <div>
            <h2 className="font-semibold text-slate-900">Quick reference</h2>
            <table className="mt-3 w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-2 pr-4 font-medium">Feature</th>
                  <th className="pb-2 pr-4 font-medium">Key required?</th>
                  <th className="pb-2 font-medium">Env variable</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                <tr className="border-b border-slate-100">
                  <td className="py-2 pr-4">Search apartments.com, rent.com &amp; other sites</td>
                  <td className="py-2 pr-4">No</td>
                  <td className="py-2">—</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2 pr-4">Landlord phone / email (apartments.com)</td>
                  <td className="py-2 pr-4">No</td>
                  <td className="py-2">—</td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2 pr-4">AI compatibility scoring</td>
                  <td className="py-2 pr-4">Optional</td>
                  <td className="py-2">
                    <code className="text-xs">OPENAI_API_KEY</code>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 pr-4">Interactive maps</td>
                  <td className="py-2 pr-4">Optional</td>
                  <td className="py-2">
                    <code className="text-xs">MAPBOX_ACCESS_TOKEN</code>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <p className="text-sm text-slate-500">
        <Link to="/profile" className="text-indigo-600 hover:underline">
          Student profile
        </Link>{' '}
        controls campus location and budget used for search — no API key there either.
      </p>
    </div>
  )
}
