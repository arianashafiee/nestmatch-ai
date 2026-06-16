import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { fetchProfile, saveProfile } from '@/lib/api'
import {
  defaultStudentProfile,
  type StudentProfile,
} from '@/types/studentProfile'

interface StudentProfileContextValue {
  profile: StudentProfile
  updateProfile: (updates: Partial<StudentProfile>) => void
  saveProfileToServer: (profile?: StudentProfile) => Promise<void>
  resetProfile: () => void
  isProfileComplete: boolean
  isSaving: boolean
  isSyncedWithServer: boolean
  saveError: string | null
}

const StudentProfileContext = createContext<StudentProfileContextValue | null>(
  null,
)

const STORAGE_KEY = 'nestmatch-student-profile'

function loadProfile(): StudentProfile {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...defaultStudentProfile, ...JSON.parse(stored) }
    }
  } catch {
    // ignore parse errors
  }
  return defaultStudentProfile
}

function persistLocal(profile: StudentProfile) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
}

function isComplete(profile: StudentProfile): boolean {
  return (
    profile.university.trim().length > 0 &&
    profile.campusLocation.trim().length > 0 &&
    profile.maxRent > 0
  )
}

export function StudentProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<StudentProfile>(loadProfile)
  const [isSaving, setIsSaving] = useState(false)
  const [isSyncedWithServer, setIsSyncedWithServer] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    fetchProfile()
      .then((serverProfile) => {
        setProfile(serverProfile)
        persistLocal(serverProfile)
        setIsSyncedWithServer(true)
      })
      .catch(() => {
        setIsSyncedWithServer(false)
      })
  }, [])

  const updateProfile = useCallback((updates: Partial<StudentProfile>) => {
    setProfile((prev) => {
      const next = { ...prev, ...updates }
      persistLocal(next)
      return next
    })
    setSaveError(null)
  }, [])

  const saveProfileToServer = useCallback(
    async (profileToSave?: StudentProfile) => {
      const payload = profileToSave ?? profile
      setIsSaving(true)
      setSaveError(null)
      try {
        const saved = await saveProfile(payload)
        setProfile(saved)
        persistLocal(saved)
        setIsSyncedWithServer(true)
      } catch (err) {
        setSaveError(
          err instanceof Error ? err.message : 'Failed to save profile',
        )
        throw err
      } finally {
        setIsSaving(false)
      }
    },
    [profile],
  )

  const resetProfile = useCallback(() => {
    setProfile(defaultStudentProfile)
    localStorage.removeItem(STORAGE_KEY)
    setSaveError(null)
  }, [])

  const value = useMemo(
    () => ({
      profile,
      updateProfile,
      saveProfileToServer,
      resetProfile,
      isProfileComplete: isComplete(profile),
      isSaving,
      isSyncedWithServer,
      saveError,
    }),
    [
      profile,
      updateProfile,
      saveProfileToServer,
      resetProfile,
      isSaving,
      isSyncedWithServer,
      saveError,
    ],
  )

  return (
    <StudentProfileContext.Provider value={value}>
      {children}
    </StudentProfileContext.Provider>
  )
}

export function useStudentProfile(): StudentProfileContextValue {
  const context = useContext(StudentProfileContext)
  if (!context) {
    throw new Error(
      'useStudentProfile must be used within a StudentProfileProvider',
    )
  }
  return context
}
