import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export interface AuthUser {
  id: number
  email: string
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'nestmatch-auth-token'
const USER_KEY = 'nestmatch-auth-user'

function loadStoredAuth(): { user: AuthUser | null; token: string | null } {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const userRaw = localStorage.getItem(USER_KEY)
    if (token && userRaw) {
      return { token, user: JSON.parse(userRaw) as AuthUser }
    }
  } catch {
    // ignore
  }
  return { user: null, token: null }
}

function persistAuth(user: AuthUser, token: string) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

function clearAuthStorage() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = loadStoredAuth()
  const [user, setUser] = useState<AuthUser | null>(stored.user)
  const [token, setToken] = useState<string | null>(stored.token)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function verifySession() {
      if (!stored.token) {
        setIsLoading(false)
        return
      }
      try {
        const { fetchCurrentUser } = await import('@/lib/api')
        const current = await fetchCurrentUser()
        setUser(current)
        setToken(stored.token)
        persistAuth(current, stored.token!)
      } catch {
        clearAuthStorage()
        setUser(null)
        setToken(null)
      } finally {
        setIsLoading(false)
      }
    }
    verifySession()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email: string, password: string) => {
    const { loginUser } = await import('@/lib/api')
    const result = await loginUser(email, password)
    setUser(result.user)
    setToken(result.accessToken)
    persistAuth(result.user, result.accessToken)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    const { registerUser } = await import('@/lib/api')
    const result = await registerUser(email, password)
    setUser(result.user)
    setToken(result.accessToken)
    persistAuth(result.user, result.accessToken)
  }, [])

  const logout = useCallback(() => {
    clearAuthStorage()
    setUser(null)
    setToken(null)
  }, [])

  const value = useMemo(
    () => ({ user, token, isLoading, login, register, logout }),
    [user, token, isLoading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function profileStorageKey(userId: number): string {
  return `nestmatch-student-profile-${userId}`
}

export function apartmentsStorageKey(userId: number): string {
  return `nestmatch-apartments-${userId}`
}
