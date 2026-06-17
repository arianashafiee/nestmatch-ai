import { useEffect, useState } from 'react'
import {
  Bike,
  Bus,
  CheckCircle2,
  Footprints,
  Loader2,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { StepIndicator } from '@/components/ui/StepIndicator'
import { TagToggle } from '@/components/ui/TagToggle'
import { useStudentProfile } from '@/context/StudentProfileContext'
import { cn } from '@/lib/utils'
import {
  AMENITY_OPTIONS,
  COMMUTE_OPTIONS,
  LEASE_LENGTH_OPTIONS,
  type AmenityTag,
  type CommuteMode,
  type StudentProfile,
} from '@/types/studentProfile'

const STEPS = ['Campus & Budget', 'Commute & Living', 'Contact & Lease', 'Preferences']

const commuteIcons: Record<CommuteMode, typeof Footprints> = {
  walking: Footprints,
  transit: Bus,
  biking: Bike,
}

interface StudentProfileFormProps {
  onSaved?: () => void
}

export function StudentProfileForm({ onSaved }: StudentProfileFormProps) {
  const {
    profile,
    updateProfile,
    saveProfileToServer,
    isSaving,
    isSyncedWithServer,
    saveError,
  } = useStudentProfile()

  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState<StudentProfile>(profile)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)
  const [localSaveWarning, setLocalSaveWarning] = useState<string | null>(null)

  useEffect(() => {
    setDraft(profile)
  }, [profile])

  const updateDraft = (updates: Partial<StudentProfile>) => {
    setDraft((prev) => ({ ...prev, ...updates }))
    setSaved(false)
    setErrors({})
  }

  const toggleAmenity = (
    field: 'mustHaves' | 'dealbreakers',
    tag: AmenityTag,
  ) => {
    const list = draft[field]
    const next = list.includes(tag)
      ? list.filter((t) => t !== tag)
      : [...list, tag]
    updateDraft({ [field]: next })
  }

  const validateStep = (currentStep: number): boolean => {
    const nextErrors: Record<string, string> = {}

    if (currentStep === 0) {
      if (!draft.university.trim()) nextErrors.university = 'Required'
      if (!draft.campusLocation.trim())
        nextErrors.campusLocation = 'Required'
      if (draft.maxRent <= 0) nextErrors.maxRent = 'Must be greater than 0'
    }

    if (currentStep === 1) {
      if (draft.maxCommuteMinutes <= 0)
        nextErrors.maxCommuteMinutes = 'Must be greater than 0'
      if (
        draft.livingSituation === 'roommates' &&
        draft.roommateCount < 1
      ) {
        nextErrors.roommateCount = 'Enter number of roommates'
      }
    }

    if (currentStep === 2) {
      if (!draft.fullName.trim()) nextErrors.fullName = 'Required'
      if (!draft.phoneNumber.trim()) nextErrors.phoneNumber = 'Required'
      if (!draft.preferredLeaseLength.trim())
        nextErrors.preferredLeaseLength = 'Select your preferred lease length'
    }

    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleNext = () => {
    if (!validateStep(step)) return
    setStep((s) => Math.min(s + 1, STEPS.length - 1))
  }

  const handleBack = () => setStep((s) => Math.max(s - 1, 0))

  const handleSave = async () => {
    for (let i = 0; i < STEPS.length; i++) {
      if (!validateStep(i)) {
        setStep(i)
        return
      }
    }
    updateProfile(draft)
    setLocalSaveWarning(null)
    try {
      await saveProfileToServer(draft)
      setSaved(true)
    } catch (err) {
      setSaved(true)
      setLocalSaveWarning(
        err instanceof Error
          ? err.message
          : 'Could not reach the server — profile saved in your browser.',
      )
    }
    onSaved?.()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <StepIndicator steps={STEPS} currentStep={step} />
        <span
          className={cn(
            'text-xs font-medium',
            isSyncedWithServer ? 'text-emerald-600' : 'text-amber-600',
          )}
        >
          {isSyncedWithServer ? 'Synced with server' : 'Local only — server offline'}
        </span>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {step === 0 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Where are you studying?
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                We use this to estimate commute times and neighborhood fit.
              </p>
            </div>
            <Input
              id="university"
              label="University"
              placeholder="e.g. University of Michigan"
              value={draft.university}
              onChange={(e) => updateDraft({ university: e.target.value })}
              error={errors.university}
            />
            <Input
              id="campusLocation"
              label="Campus location"
              placeholder="e.g. Ann Arbor, MI or specific campus address"
              value={draft.campusLocation}
              onChange={(e) => updateDraft({ campusLocation: e.target.value })}
              error={errors.campusLocation}
            />
            <div>
              <label className="text-sm font-medium text-slate-700">
                Max monthly rent: ${draft.maxRent}
              </label>
              <input
                type="range"
                min={300}
                max={5000}
                step={50}
                value={draft.maxRent}
                onChange={(e) =>
                  updateDraft({ maxRent: Number(e.target.value) })
                }
                className="mt-2 w-full accent-indigo-600"
              />
              <div className="mt-1 flex justify-between text-xs text-slate-400">
                <span>$300</span>
                <span>$5,000</span>
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                How do you get to campus?
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Set your ideal commute time and transportation preference.
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">
                Max commute: {draft.maxCommuteMinutes} min
              </label>
              <input
                type="range"
                min={5}
                max={90}
                step={5}
                value={draft.maxCommuteMinutes}
                onChange={(e) =>
                  updateDraft({ maxCommuteMinutes: Number(e.target.value) })
                }
                className="mt-2 w-full accent-indigo-600"
              />
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700">Commute mode</p>
              <div className="flex flex-wrap gap-2">
                {COMMUTE_OPTIONS.map(({ value, label }) => {
                  const Icon = commuteIcons[value]
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => updateDraft({ commuteMode: value })}
                      className={cn(
                        'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                        draft.commuteMode === value
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300',
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700">
                Living situation
              </p>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    { value: 'solo', label: 'Solo' },
                    { value: 'roommates', label: 'With roommates' },
                  ] as const
                ).map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() =>
                      updateDraft({
                        livingSituation: value,
                        roommateCount: value === 'solo' ? 0 : draft.roommateCount || 1,
                      })
                    }
                    className={cn(
                      'flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                      draft.livingSituation === value
                        ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300',
                    )}
                  >
                    {value === 'roommates' && <Users className="h-4 w-4" />}
                    {label}
                  </button>
                ))}
              </div>
              {draft.livingSituation === 'roommates' && (
                <Input
                  id="roommateCount"
                  label="Number of roommates"
                  type="number"
                  min={1}
                  max={10}
                  value={draft.roommateCount || ''}
                  onChange={(e) =>
                    updateDraft({ roommateCount: Number(e.target.value) })
                  }
                  error={errors.roommateCount}
                />
              )}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Contact & lease preferences
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Used in your landlord outreach emails and to match listings to your
                preferred lease term.
              </p>
            </div>
            <Input
              id="fullName"
              label="Your name"
              placeholder="e.g. Alex Johnson"
              value={draft.fullName}
              onChange={(e) => updateDraft({ fullName: e.target.value })}
              error={errors.fullName}
            />
            <Input
              id="phoneNumber"
              label="Phone number"
              type="tel"
              placeholder="e.g. (410) 555-0123"
              value={draft.phoneNumber}
              onChange={(e) => updateDraft({ phoneNumber: e.target.value })}
              error={errors.phoneNumber}
            />
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700">
                Preferred lease length
              </p>
              <div className="flex flex-wrap gap-2">
                {LEASE_LENGTH_OPTIONS.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => updateDraft({ preferredLeaseLength: value })}
                    className={cn(
                      'rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors',
                      draft.preferredLeaseLength === value
                        ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300',
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {errors.preferredLeaseLength && (
                <p className="text-sm text-red-600">{errors.preferredLeaseLength}</p>
              )}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Must-haves & dealbreakers
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Toggle tags to tell NestMatch what matters most to you.
              </p>
            </div>
            <div className="space-y-3">
              <p className="text-sm font-medium text-emerald-700">Must-haves</p>
              <div className="flex flex-wrap gap-2">
                {AMENITY_OPTIONS.map(({ value, label }) => (
                  <TagToggle
                    key={`must-${value}`}
                    label={label}
                    selected={draft.mustHaves.includes(value)}
                    onToggle={() => toggleAmenity('mustHaves', value)}
                    variant="must-have"
                  />
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <p className="text-sm font-medium text-red-600">Dealbreakers</p>
              <div className="flex flex-wrap gap-2">
                {AMENITY_OPTIONS.map(({ value, label }) => (
                  <TagToggle
                    key={`deal-${value}`}
                    label={label}
                    selected={draft.dealbreakers.includes(value)}
                    onToggle={() => toggleAmenity('dealbreakers', value)}
                    variant="dealbreaker"
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {(localSaveWarning || saveError) && (
        <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {localSaveWarning ?? saveError} Your profile is saved in this browser.
        </p>
      )}

      {saved && !localSaveWarning && !saveError && (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Profile saved successfully.
        </div>
      )}

      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={handleBack}
          disabled={step === 0}
        >
          Back
        </Button>
        <div className="flex gap-2">
          {step < STEPS.length - 1 ? (
            <Button onClick={handleNext}>Continue</Button>
          ) : (
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Profile'
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
