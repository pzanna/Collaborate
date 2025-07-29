import { createContext, useContext, useState, useEffect } from "react"
import type { ReactNode } from "react"

interface User {
  id: number
  username: string
  email: string
  full_name: string
  role: string
  is_2fa_enabled: boolean
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (accessToken: string, refreshToken: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isAuthenticated = !!user

  const login = async (accessToken: string, refreshToken: string) => {
    localStorage.setItem("access_token", accessToken)
    localStorage.setItem("refresh_token", refreshToken)

    try {
      const response = await fetch("http://localhost:8013/users/me", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      }
    } catch (error) {
      console.error("Failed to fetch user data:", error)
    }
  }

  const logout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    setUser(null)
  }

  const refreshToken = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem("refresh_token")
    if (!refreshToken) return false

    try {
      const response = await fetch(
        `http://localhost:8013/refresh?refresh_token=${encodeURIComponent(
          refreshToken
        )}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      )

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem("access_token", data.access_token)
        return true
      }
    } catch (error) {
      console.error("Token refresh failed:", error)
    }

    logout()
    return false
  }

  // Check for existing auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      const accessToken = localStorage.getItem("access_token")
      if (!accessToken) {
        setIsLoading(false)
        return
      }

      try {
        const response = await fetch("http://localhost:8013/users/me", {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        })

        if (response.ok) {
          const userData = await response.json()
          setUser(userData)
        } else if (response.status === 401) {
          // Try to refresh token
          if (!(await refreshToken())) {
            logout()
          } else {
            // Retry with new token
            await checkAuth()
            return
          }
        }
      } catch (error) {
        console.error("Auth check failed:", error)
        logout()
      }

      setIsLoading(false)
    }

    checkAuth()
  }, [])

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
