import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react"
import type { ReactNode } from "react"

interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  is_2fa_enabled: boolean
  profile_image_url?: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  authError: string | null
  login: (accessToken: string, refreshToken: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<boolean>
  refreshUserData: () => Promise<void>
  clearAuthError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

// Constants for better maintainability
const AUTH_ENDPOINTS = {
  USERS_ME: "http://localhost:8013/users/me",
  REFRESH: "http://localhost:8013/refresh",
  AUTH_PAGE: "/auth",
}

const TOKEN_VALIDATION = {
  MIN_LENGTH: 50,
  REQUIRED_PARTS: 3, // JWT has 3 parts separated by dots
  SEPARATOR: ".",
}

const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  REFRESH_TOKEN: "refresh_token",
}

// Utility functions for token validation
const isValidJWT = (token: string | null): boolean => {
  if (!token || token === "undefined" || token === "null") return false

  const parts = token.split(TOKEN_VALIDATION.SEPARATOR)
  if (parts.length !== TOKEN_VALIDATION.REQUIRED_PARTS) return false

  if (token.length < TOKEN_VALIDATION.MIN_LENGTH) return false

  // Basic JWT structure validation
  try {
    const header = JSON.parse(atob(parts[0]))
    const payload = JSON.parse(atob(parts[1]))

    // Check if token has expired (with 30 second buffer)
    if (payload.exp && Date.now() > payload.exp * 1000 - 30000) {
      console.log("Token expired or expiring soon")
      return false
    }

    return !!(header && payload && parts[2]) // Has all required parts
  } catch (error) {
    console.log("Invalid JWT format:", error)
    return false
  }
}

const clearStoredTokens = (): void => {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
  // Clear any other potentially stale auth data
  localStorage.removeItem("user")
  localStorage.removeItem("user_data")
}

const getStoredToken = (key: string): string | null => {
  try {
    return localStorage.getItem(key)
  } catch (error) {
    console.error("Failed to access localStorage:", error)
    return null
  }
}

const setStoredToken = (key: string, value: string): void => {
  try {
    localStorage.setItem(key, value)
  } catch (error) {
    console.error("Failed to store token:", error)
  }
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)

  const isAuthenticated = !!user

  const clearAuthError = useCallback(() => {
    setAuthError(null)
  }, [])

  const handleAuthError = useCallback((error: string, shouldLogout = true) => {
    console.error("Auth error:", error)
    setAuthError(error)
    if (shouldLogout) {
      clearStoredTokens()
      setUser(null)
    }
  }, [])

  const login = async (accessToken: string, refreshToken: string) => {
    clearAuthError()

    if (!isValidJWT(accessToken) || !isValidJWT(refreshToken)) {
      handleAuthError("Invalid tokens provided", false)
      return
    }

    setStoredToken(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
    setStoredToken(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)

    try {
      const response = await fetch(AUTH_ENDPOINTS.USERS_ME, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        console.log("User login successful:", userData.email)
      } else {
        throw new Error(`Failed to fetch user data: ${response.status}`)
      }
    } catch (error) {
      handleAuthError("Failed to complete login process", false)
      console.error("Login error:", error)
    }
  }

  const logout = useCallback(() => {
    console.log("Logging out user")
    clearStoredTokens()
    setUser(null)
    setAuthError(null)

    // Navigate to auth page
    if (typeof window !== "undefined") {
      window.location.href = AUTH_ENDPOINTS.AUTH_PAGE
    }
  }, [])

  const refreshToken = useCallback(async (): Promise<boolean> => {
    const storedRefreshToken = getStoredToken(STORAGE_KEYS.REFRESH_TOKEN)

    console.log("Attempting token refresh...", {
      hasRefreshToken: !!storedRefreshToken,
      refreshTokenLength: storedRefreshToken?.length || 0,
    })

    if (!isValidJWT(storedRefreshToken)) {
      console.log("No valid refresh token found")
      handleAuthError("Invalid or expired refresh token")
      return false
    }

    try {
      const response = await fetch(
        `${AUTH_ENDPOINTS.REFRESH}?refresh_token=${encodeURIComponent(
          storedRefreshToken!
        )}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      )

      console.log("Refresh response status:", response.status)

      if (response.ok) {
        const data = await response.json()
        console.log("Token refresh successful")

        if (!isValidJWT(data.access_token)) {
          throw new Error("Received invalid access token from refresh")
        }

        setStoredToken(STORAGE_KEYS.ACCESS_TOKEN, data.access_token)
        if (data.refresh_token && isValidJWT(data.refresh_token)) {
          setStoredToken(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token)
        }

        clearAuthError()
        return true
      } else {
        const errorData = await response.json().catch(() => ({}))
        console.log("Token refresh failed:", response.status, errorData)
        throw new Error(`Token refresh failed: ${response.status}`)
      }
    } catch (error) {
      console.error("Token refresh network error:", error)
      handleAuthError("Token refresh failed")
      return false
    }
  }, [handleAuthError])

  const refreshUserData = useCallback(async () => {
    const accessToken = getStoredToken(STORAGE_KEYS.ACCESS_TOKEN)

    if (!isValidJWT(accessToken)) {
      console.log("No valid access token for user data refresh")
      return
    }

    try {
      const response = await fetch(AUTH_ENDPOINTS.USERS_ME, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        clearAuthError()
      } else if (response.status === 401) {
        console.log(
          "Access token expired during user data refresh, attempting refresh..."
        )
        const refreshSuccessful = await refreshToken()
        if (refreshSuccessful) {
          // Retry with new token
          const newAccessToken = getStoredToken(STORAGE_KEYS.ACCESS_TOKEN)
          if (newAccessToken) {
            const retryResponse = await fetch(AUTH_ENDPOINTS.USERS_ME, {
              headers: {
                Authorization: `Bearer ${newAccessToken}`,
              },
            })

            if (retryResponse.ok) {
              const userData = await retryResponse.json()
              setUser(userData)
              clearAuthError()
            }
          }
        }
      } else {
        throw new Error(`Failed to refresh user data: ${response.status}`)
      }
    } catch (error) {
      console.error("Failed to refresh user data:", error)
      handleAuthError("Failed to refresh user data", false)
    }
  }, [refreshToken, handleAuthError, clearAuthError])

  // Check for existing auth on mount with enhanced error handling
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const accessToken = getStoredToken(STORAGE_KEYS.ACCESS_TOKEN)
        const refreshTokenValue = getStoredToken(STORAGE_KEYS.REFRESH_TOKEN)

        console.log("Initial auth check...", {
          hasAccessToken: !!accessToken,
          hasRefreshToken: !!refreshTokenValue,
          tokenLength: accessToken?.length || 0,
        })

        // If no tokens or invalid tokens, clear everything and finish loading
        if (!isValidJWT(accessToken) && !isValidJWT(refreshTokenValue)) {
          console.log("No valid tokens found - clearing auth data")
          clearStoredTokens()
          setIsLoading(false)
          return
        }

        // If access token is invalid but refresh token is valid, try refresh first
        if (!isValidJWT(accessToken) && isValidJWT(refreshTokenValue)) {
          console.log(
            "Access token invalid, attempting refresh before auth check..."
          )
          const refreshSuccessful = await refreshToken()
          if (!refreshSuccessful) {
            setIsLoading(false)
            return
          }
        }

        // Get the current (possibly refreshed) access token
        const currentAccessToken = getStoredToken(STORAGE_KEYS.ACCESS_TOKEN)
        if (!isValidJWT(currentAccessToken)) {
          console.log("Still no valid access token after refresh attempt")
          handleAuthError("Unable to obtain valid access token")
          setIsLoading(false)
          return
        }

        // Attempt to fetch user data
        const response = await fetch(AUTH_ENDPOINTS.USERS_ME, {
          headers: {
            Authorization: `Bearer ${currentAccessToken}`,
          },
        })

        console.log("User fetch response status:", response.status)

        if (response.ok) {
          const userData = await response.json()
          console.log("User authenticated successfully:", userData.email)
          setUser(userData)
          clearAuthError()
        } else if (response.status === 401) {
          console.log("Access token expired, attempting refresh...")
          const refreshSuccessful = await refreshToken()

          if (refreshSuccessful) {
            // Retry with new token
            const newAccessToken = getStoredToken(STORAGE_KEYS.ACCESS_TOKEN)
            if (newAccessToken) {
              const retryResponse = await fetch(AUTH_ENDPOINTS.USERS_ME, {
                headers: {
                  Authorization: `Bearer ${newAccessToken}`,
                },
              })

              if (retryResponse.ok) {
                const userData = await retryResponse.json()
                console.log("User authenticated after refresh:", userData.email)
                setUser(userData)
                clearAuthError()
              } else {
                console.log("Failed to authenticate after refresh")
                handleAuthError("Authentication failed after token refresh")
              }
            } else {
              console.log("No new access token after refresh")
              handleAuthError("No access token received after refresh")
            }
          }
        } else {
          console.log("Unexpected auth response:", response.status)
          handleAuthError(
            `Authentication failed with status: ${response.status}`
          )
        }
      } catch (error) {
        console.error("Auth check failed:", error)
        handleAuthError("Authentication check failed due to network error")
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [refreshToken, handleAuthError, clearAuthError])

  const value = {
    user,
    isAuthenticated,
    isLoading,
    authError,
    login,
    logout,
    refreshToken,
    refreshUserData,
    clearAuthError,
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
