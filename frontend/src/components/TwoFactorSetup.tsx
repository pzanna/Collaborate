import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

export function TwoFactorSetup() {
  const [qrCodeUrl, setQrCodeUrl] = useState<string>("")
  const [qrCodeImageUrl, setQrCodeImageUrl] = useState<string>("")
  const [secret, setSecret] = useState<string>("")
  const [totpCode, setTotpCode] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [isEnabled, setIsEnabled] = useState(false)
  const [error, setError] = useState<string>("")
  const [success, setSuccess] = useState<string>("")

  useEffect(() => {
    // Check if 2FA is already enabled
    checkTwoFactorStatus()
    
    // Cleanup blob URL when component unmounts
    return () => {
      if (qrCodeImageUrl) {
        URL.revokeObjectURL(qrCodeImageUrl)
      }
    }
  }, [qrCodeImageUrl])

  const checkTwoFactorStatus = async () => {
    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch("http://localhost:8013/users/me", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setIsEnabled(userData.is_2fa_enabled || false)
      }
    } catch (error) {
      console.error("Error checking 2FA status:", error)
    }
  }

  const fetchQrCodeImage = async () => {
    try {
      const token = localStorage.getItem("access_token")
      if (!token) {
        setError("No authentication token found")
        return
      }

      const response = await fetch("http://localhost:8013/2fa/qrcode", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        setQrCodeImageUrl(imageUrl)
      } else {
        setError("Failed to load QR code image")
      }
    } catch (error) {
      console.error("Error fetching QR code image:", error)
      setError("Error loading QR code image")
    }
  }

  const setupTwoFactor = async () => {
    setIsLoading(true)
    setError("")
    setSuccess("")

    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch("http://localhost:8013/2fa/setup", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      const data = await response.json()

      if (response.ok) {
        setQrCodeUrl(data.qr_code_url)
        setSecret(data.secret_key)
        // Fetch the QR code image
        await fetchQrCodeImage()
      } else {
        setError(data.detail || "Failed to setup 2FA")
      }
    } catch (error) {
      setError("Network error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const verifyTwoFactor = async () => {
    if (!totpCode.trim()) {
      setError("Please enter a verification code")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch("http://localhost:8013/2fa/verify", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          totp_code: totpCode,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess("2FA has been successfully enabled!")
        setIsEnabled(true)
        setQrCodeUrl("")
        setSecret("")
        setTotpCode("")
      } else {
        setError(data.detail || "Verification failed")
      }
    } catch (error) {
      setError("Network error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const disableTwoFactor = async () => {
    if (
      !confirm(
        "Are you sure you want to disable 2FA? This will make your account less secure."
      )
    ) {
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch("http://localhost:8013/2fa/disable", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          password: "dummypassword", // This would need to be collected from user
        }),
      })

      if (response.ok) {
        setSuccess("2FA has been disabled")
        setIsEnabled(false)
      } else {
        const data = await response.json()
        setError(data.detail || "Failed to disable 2FA")
      }
    } catch (error) {
      setError("Network error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl flex items-center justify-center gap-2">
            Two-Factor Authentication
            {isEnabled && <Badge variant="default">Enabled</Badge>}
          </CardTitle>
          <CardDescription>
            {isEnabled
              ? "Your account is protected with 2FA"
              : "Add an extra layer of security to your account"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="text-sm text-red-500 text-center bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          {success && (
            <div className="text-sm text-green-500 text-center bg-green-50 p-2 rounded">
              {success}
            </div>
          )}

          {!isEnabled && !qrCodeUrl && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Two-factor authentication adds an extra layer of security to
                your account. You'll need an authenticator app like Google
                Authenticator or Microsoft Authenticator.
              </p>
              <Button
                onClick={setupTwoFactor}
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? "Setting up..." : "Setup 2FA"}
              </Button>
            </div>
          )}

          {qrCodeUrl && (
            <div className="space-y-4">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  Scan this QR code with your authenticator app:
                </p>
                {qrCodeImageUrl ? (
                  <img
                    src={qrCodeImageUrl}
                    alt="QR Code"
                    className="mx-auto border rounded"
                  />
                ) : (
                  <div className="mx-auto w-64 h-64 border rounded flex items-center justify-center text-muted-foreground">
                    Loading QR Code...
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-2">
                  Or enter this secret manually:{" "}
                  <code className="bg-gray-100 px-1 rounded text-xs">
                    {secret}
                  </code>
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="totpCode">
                  Enter verification code from your app:
                </Label>
                <Input
                  id="totpCode"
                  type="text"
                  placeholder="123456"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  maxLength={6}
                />
              </div>

              <Button
                onClick={verifyTwoFactor}
                disabled={isLoading || !totpCode.trim()}
                className="w-full"
              >
                {isLoading ? "Verifying..." : "Verify & Enable 2FA"}
              </Button>
            </div>
          )}

          {isEnabled && (
            <div className="space-y-4">
              <p className="text-sm text-green-600 text-center">
                ✓ Two-factor authentication is enabled and protecting your
                account.
              </p>
              <Button
                onClick={disableTwoFactor}
                disabled={isLoading}
                variant="destructive"
                className="w-full"
              >
                {isLoading ? "Disabling..." : "Disable 2FA"}
              </Button>
            </div>
          )}

          <div className="text-center">
            <a
              href="/"
              className="text-sm text-muted-foreground hover:underline"
            >
              ← Back to Dashboard
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
