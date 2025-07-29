/**
 * Authentication Fix Utility
 *
 * This utility helps debug and fix authentication issues by clearing
 * stored tokens and providing debugging information.
 */

// Constants matching the useAuth hook
const TOKEN_VALIDATION = {
  MIN_LENGTH: 50,
  REQUIRED_PARTS: 3,
  SEPARATOR: ".",
}

const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  REFRESH_TOKEN: "refresh_token",
}

/**
 * Validates if a token has the correct JWT format
 */
export function isValidJWTFormat(token: string | null): boolean {
  if (!token || token === "undefined" || token === "null") return false

  const parts = token.split(TOKEN_VALIDATION.SEPARATOR)
  if (parts.length !== TOKEN_VALIDATION.REQUIRED_PARTS) return false

  if (token.length < TOKEN_VALIDATION.MIN_LENGTH) return false

  try {
    const header = JSON.parse(atob(parts[0]))
    const payload = JSON.parse(atob(parts[1]))
    return !!(header && payload && parts[2])
  } catch {
    return false
  }
}

/**
 * Checks if a JWT token is expired
 */
export function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(TOKEN_VALIDATION.SEPARATOR)
    const payload = JSON.parse(atob(parts[1]))

    if (!payload.exp) return false

    // Add 30 second buffer for clock skew
    return Date.now() > payload.exp * 1000 - 30000
  } catch {
    return true
  }
}

/**
 * Clears all authentication data and related storage
 */
export function clearAuthData(): void {
  console.log("🧹 Clearing authentication data...")

  // Clear all auth-related localStorage items
  const keysToRemove = [
    STORAGE_KEYS.ACCESS_TOKEN,
    STORAGE_KEYS.REFRESH_TOKEN,
    "user",
    "user_data",
    "auth_error",
    "last_login",
  ]

  keysToRemove.forEach((key) => {
    try {
      localStorage.removeItem(key)
    } catch (error) {
      console.warn(`Failed to remove ${key}:`, error)
    }
  })

  console.log(
    "✅ Authentication data cleared. Please refresh the page and login again."
  )
}

/**
 * Forces a complete auth reset and page reload
 */
export function forceAuthReset(): void {
  console.log("🔄 Forcing complete authentication reset...")
  clearAuthData()

  // Clear any cached auth context
  if (typeof window !== "undefined") {
    setTimeout(() => {
      window.location.href = "/auth"
    }, 100)
  }
}

/**
 * Comprehensive authentication state debugging
 */
export function debugAuthState(): void {
  console.log("🔍 === Authentication Debug Info ===")

  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)

  console.log("📊 Token Status:")
  console.log("  Access Token:", accessToken ? "Present" : "❌ Missing")
  console.log("  Refresh Token:", refreshToken ? "Present" : "❌ Missing")

  if (accessToken) {
    console.log("\n🔑 Access Token Analysis:")
    console.log("  Length:", accessToken.length)
    console.log(
      "  Valid Format:",
      isValidJWTFormat(accessToken) ? "✅ Valid" : "❌ Invalid"
    )

    if (isValidJWTFormat(accessToken)) {
      try {
        const parts = accessToken.split(TOKEN_VALIDATION.SEPARATOR)
        const payload = JSON.parse(atob(parts[1]))
        const isExpired = isTokenExpired(accessToken)

        console.log("  Payload:", payload)
        console.log(
          "  Issued At:",
          payload.iat ? new Date(payload.iat * 1000) : "Unknown"
        )
        console.log(
          "  Expires At:",
          payload.exp ? new Date(payload.exp * 1000) : "Unknown"
        )
        console.log("  Expired:", isExpired ? "❌ Yes" : "✅ No")
        console.log("  User Email:", payload.sub || "Unknown")
        console.log("  User Role:", payload.role || "Unknown")
      } catch (error) {
        console.log("  ❌ Token parsing error:", error)
      }
    } else {
      console.log("  ❌ Token appears corrupted (invalid format or too short)")
    }
  }

  if (refreshToken) {
    console.log("\n🔄 Refresh Token Analysis:")
    console.log("  Length:", refreshToken.length)
    console.log(
      "  Valid Format:",
      isValidJWTFormat(refreshToken) ? "✅ Valid" : "❌ Invalid"
    )

    if (isValidJWTFormat(refreshToken)) {
      try {
        const parts = refreshToken.split(TOKEN_VALIDATION.SEPARATOR)
        const payload = JSON.parse(atob(parts[1]))
        const isExpired = isTokenExpired(refreshToken)

        console.log(
          "  Expires At:",
          payload.exp ? new Date(payload.exp * 1000) : "Unknown"
        )
        console.log("  Expired:", isExpired ? "❌ Yes" : "✅ No")
        console.log("  Type:", payload.type || "Unknown")
      } catch (error) {
        console.log("  ❌ Token parsing error:", error)
      }
    } else {
      console.log("  ❌ Refresh token appears corrupted")
    }
  }

  console.log("\n🌐 Environment Info:")
  console.log("  Current URL:", window.location.href)
  console.log("  User Agent:", navigator.userAgent.substring(0, 50) + "...")
  console.log("  Local Storage Available:", typeof Storage !== "undefined")

  // Check if backend is reachable
  fetch("http://localhost:8013/health")
    .then((response) => {
      console.log(
        "  Backend Health:",
        response.ok ? "✅ Healthy" : "❌ Unhealthy"
      )
    })
    .catch(() => {
      console.log("  Backend Health: ❌ Unreachable")
    })

  console.log("🔍 === End Debug Info ===")
}

/**
 * Quick health check for authentication system
 */
export function quickAuthCheck(): void {
  const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
  const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)

  console.log("⚡ Quick Auth Check:")

  if (!accessToken && !refreshToken) {
    console.log("❌ No tokens found - user needs to login")
    return
  }

  if (
    accessToken &&
    isValidJWTFormat(accessToken) &&
    !isTokenExpired(accessToken)
  ) {
    console.log("✅ Access token is valid and not expired")
    return
  }

  if (
    refreshToken &&
    isValidJWTFormat(refreshToken) &&
    !isTokenExpired(refreshToken)
  ) {
    console.log("⚠️ Access token invalid/expired, but refresh token is valid")
    return
  }

  console.log(
    "❌ All tokens are invalid or expired - clear auth data and re-login"
  )
}

// Make functions available globally for debugging
if (typeof window !== "undefined") {
  const authDebug = {
    clearAuthData,
    forceAuthReset,
    debugAuthState,
    quickAuthCheck,
    isValidJWTFormat,
    isTokenExpired,
  }

  ;(window as any).authDebug = authDebug

  // Backward compatibility
  ;(window as any).clearAuthData = clearAuthData
  ;(window as any).debugAuthState = debugAuthState

  console.log(
    "🔧 Auth debugging tools loaded. Use 'authDebug' object or individual functions:"
  )
  console.log("  - authDebug.debugAuthState() - Full debug info")
  console.log("  - authDebug.quickAuthCheck() - Quick status check")
  console.log("  - authDebug.clearAuthData() - Clear all auth data")
  console.log("  - authDebug.forceAuthReset() - Complete reset + redirect")
}
