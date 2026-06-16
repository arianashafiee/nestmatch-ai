import { ExternalLink, Mail, Phone, User } from 'lucide-react'
import type { LandlordContact } from '@/types/apartment'

interface LandlordContactCardProps {
  contact: LandlordContact | null | undefined
  sourceUrl?: string | null
}

export function LandlordContactCard({
  contact,
  sourceUrl,
}: LandlordContactCardProps) {
  const hasContact =
    contact &&
    (contact.name || contact.phone || contact.email || contact.contactUrl)

  if (!hasContact) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-600">
        <p className="font-medium text-slate-800">Landlord contact</p>
        <p className="mt-1">
          No phone or email found yet. Paste an{' '}
          <strong>apartments.com</strong> listing URL and click{' '}
          <strong>Refresh photos</strong> on the listing page — we scrape
          contact info from the listing when available.
        </p>
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1 text-indigo-600 hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Check listing page for contact
          </a>
        )}
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-5 py-4">
      <h3 className="font-semibold text-slate-900">Landlord contact</h3>
      <ul className="mt-3 space-y-2 text-sm text-slate-700">
        {contact.name && (
          <li className="flex items-center gap-2">
            <User className="h-4 w-4 text-slate-400" />
            {contact.name}
          </li>
        )}
        {contact.phone && (
          <li className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-slate-400" />
            <a href={`tel:${contact.phone}`} className="text-indigo-600 hover:underline">
              {contact.phone}
            </a>
          </li>
        )}
        {contact.email && (
          <li className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-slate-400" />
            <a
              href={`mailto:${contact.email}`}
              className="text-indigo-600 hover:underline"
            >
              {contact.email}
            </a>
          </li>
        )}
        {contact.contactUrl && (
          <li>
            <a
              href={contact.contactUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Contact on listing site
            </a>
          </li>
        )}
      </ul>
    </div>
  )
}
