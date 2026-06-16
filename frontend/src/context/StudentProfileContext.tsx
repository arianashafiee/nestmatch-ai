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
import { useAuth, profileStorageKey } from '@/context/AuthContext'
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

function loadProfile(userId: number): StudentProfile {
  try {
    const stored = localStorage.getItem(profileStorageKey(userId))
    if (stored) {
      return { ...defaultStudentProfile, ...JSON.parse(stored) }
    }
  } catch {
    // ignore parse errors
  }
  return defaultStudentProfile
}

function persistLocal(userId: number, profile: StudentProfile) {
  localStorage.setItem(profileStorageKey(userId), JSON.stringify(profile))
}

function isComplete(profile: StudentProfile): boolean {
  return (
    profile.university.trim().length > 0 &&
    profile.campusLocation.trim().length > 0 &&
    profile.maxRent > 0
  )
}

export function StudentProfileProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [profile, setProfile] = useState<StudentProfile>(defaultStudentProfile)
  const [isSaving, setIsSaving] = useState(false)
  const [isSyncedWithServer, setIsSyncedWithServer] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      setProfile(defaultStudentProfile)
      setIsSyncedWithServer(false)
      return
    }

    setProfile(loadProfile(user.id))
    fetchProfile()
      .then((serverProfile) => {
        setProfile(serverProfile)
        persistLocal(user.id, serverProfile)
        setIsSyncedWithServer(true)
      })
      .catch(() => {
        setIsSyncedWithServer(false)
      })
  }, [user?.id])

  const updateProfile = useCallback(
    (updates: Partial<StudentProfile>) => {
      if (!user) return
      setProfile((prev) => {
        const next = { ...prev, ...updates }
        persistLocal(user.id, next)
        return next
      })
      setSaveError(null)
    },
    [user],
  )

  const saveProfileToServer = useCallback(
    async (profileToSave?: StudentProfile) => {
      if (!user) return
      const payload = profileToSave ?? profile
      setIsSaving(true)
      setSaveError(null)
      try {
        const saved = await saveProfile(payload)
        setProfile(saved)
        persistLocal(user.id, saved)
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
    [profile, user],
  )

  const resetProfile = useCallback(() => {
    if (!user) return
    setProfile(defaultStudentProfile)
    localStorage.removeItem(profileStorageKey(user.id))
    setSaveError(null)
  }, [user])

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
