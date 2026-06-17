import { Link } from 'react-router-dom'
import { useState } from 'react'
import { Check, Copy, Mail } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { generateLandlordMessage } from '@/lib/landlordMessage'
import { useStudentProfile } from '@/context/StudentProfileContext'
import type { ListingAnalysis, LandlordContact } from '@/types/apartment'

interface LandlordMessageGeneratorProps {
  analysis: ListingAnalysis
  landlordContact?: LandlordContact | null
}

export function LandlordMessageGenerator({
  analysis,
  landlordContact,
}: LandlordMessageGeneratorProps) {
  const { profile } = useStudentProfile()
  const [copied, setCopied] = useState(false)
  const message = generateLandlordMessage(analysis, profile, landlordContact)
  const missingContactInfo =
    !profile.fullName.trim() ||
    !profile.phoneNumber.trim() ||
    !profile.preferredLeaseLength.trim()

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = message
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-indigo-600" />
          <h3 className="font-semibold text-slate-900">Ask the Landlord</h3>
        </div>
        <Button size="sm" variant="outline" onClick={handleCopy}>
          {copied ? (
            <>
              <Check className="h-4 w-4 text-emerald-600" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              Copy to clipboard
            </>
          )}
        </Button>
      </div>
      {missingContactInfo && (
        <p className="border-b border-amber-100 bg-amber-50 px-5 py-3 text-sm text-amber-900">
          Add your name, phone, and preferred lease length in{' '}
          <Link to="/profile" className="font-medium text-indigo-700 underline">
            Profile settings
          </Link>{' '}
          so this email includes them in the closing.
        </p>
      )}
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap p-5 font-sans text-sm leading-relaxed text-slate-700">
        {message}
      </pre>
    </div>
  )
}
