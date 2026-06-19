import { useNavigate } from 'react-router-dom'
import { StudentProfileForm } from '@/components/profile/StudentProfileForm'
import { useStudentProfile } from '@/context/StudentProfileContext'

export function ProfilePage() {
  const navigate = useNavigate()
  const { profile, isProfileComplete } = useStudentProfile()

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">
          Your Apartment Hunt Profile
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Tell NestMatch about your budget, commute, and contact info
          so AI can score listings for you.
        </p>
        {isProfileComplete && (
          <p className="mt-2 text-sm text-indigo-600">
            Hunting near {profile.university} · ${profile.maxRent}/mo max
          </p>
        )}
      </div>
      <StudentProfileForm onSaved={() => navigate('/board')} />
    </div>
  )
}
