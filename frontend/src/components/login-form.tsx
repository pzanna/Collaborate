import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
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
import { PasswordInput } from "@/components/ui/password-input"
import { useAuth } from "@/hooks/useAuth"
import { ROUTES } from "@/utils/routes"

interface LoginFormProps extends React.ComponentProps<"div"> {
  onShowRegistration?: () => void
}

export function LoginForm({
  className,
  onShowRegistration,
  ...props
}: LoginFormProps) {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    totpCode: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [needsTwoFA, setNeedsTwoFA] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: "",
      }))
    }
  }

  const handlePasswordChange = (value: string) => {
    setFormData((prev) => ({
      ...prev,
      password: value,
    }))
    // Clear error when user starts typing
    if (errors.password) {
      setErrors((prev) => ({
        ...prev,
        password: "",
      }))
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setErrors({})

    try {
      // First, try regular login using form data
      const loginFormData = new URLSearchParams()
      loginFormData.append("username", formData.email) // Backend expects username field but we use email
      loginFormData.append("password", formData.password)

      const response = await fetch("http://localhost:8013/token", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: loginFormData,
      })

      const data = await response.json()

      if (response.ok) {
        // Login successful - no 2FA required for /token endpoint
        await login(data.access_token, data.refresh_token)
        navigate(ROUTES.WELCOME)
      } else {
        // Check if user might have 2FA enabled - try the 2FA endpoint
        setNeedsTwoFA(true)
      }
    } catch (error) {
      setErrors({ submit: "Network error. Please try again." })
    } finally {
      setIsLoading(false)
    }
  }

  const handleTwoFALogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setErrors({})

    try {
      const response = await fetch("http://localhost:8013/login-2fa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formData.email, // Backend expects username field but we use email
          password: formData.password,
          totp_code: formData.totpCode,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        // Login successful
        await login(data.access_token, data.refresh_token)
        navigate(ROUTES.WELCOME)
      } else {
        setErrors({ submit: data.detail || "2FA verification failed" })
      }
    } catch (error) {
      setErrors({ submit: "Network error. Please try again." })
    } finally {
      setIsLoading(false)
    }
  }

  const handleBackToLogin = () => {
    setNeedsTwoFA(false)
    setFormData((prev) => ({ ...prev, totpCode: "" }))
    setErrors({})
  }

  if (needsTwoFA) {
    return (
      <div className={cn("flex flex-col gap-6", className)} {...props}>
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-xl">Two-Factor Authentication</CardTitle>
            <CardDescription>
              Enter the 6-digit code from your authenticator app
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleTwoFALogin}>
              <div className="grid gap-6">
                {errors.submit && (
                  <div className="bg-destructive/15 text-destructive border border-destructive/50 rounded-md p-3 text-sm">
                    {errors.submit}
                  </div>
                )}

                <div className="grid gap-2">
                  <Label htmlFor="totpCode">Authentication Code</Label>
                  <Input
                    id="totpCode"
                    name="totpCode"
                    type="text"
                    placeholder="000000"
                    value={formData.totpCode}
                    onChange={handleChange}
                    maxLength={8}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter the 6-digit code from your authenticator app or an
                    8-character backup code
                  </p>
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? "Verifying..." : "Verify & Login"}
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={handleBackToLogin}
                >
                  Back to Login
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Welcome back</CardTitle>
          <CardDescription>
            Login to your Eunice Research account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin}>
            <div className="grid gap-6">
              {errors.submit && (
                <div className="bg-destructive/15 text-destructive border border-destructive/50 rounded-md p-3 text-sm">
                  {errors.submit}
                </div>
              )}

              <div className="flex flex-col gap-4">
                <Button variant="outline" className="w-full" disabled>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"
                      fill="currentColor"
                    />
                  </svg>
                  Login with Apple (Coming Soon)
                </Button>
                <Button variant="outline" className="w-full" disabled>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"
                      fill="currentColor"
                    />
                  </svg>
                  Login with Google (Coming Soon)
                </Button>
              </div>
              <div className="after:border-border relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t">
                <span className="bg-background relative z-10 px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>
              <div className="grid gap-6">
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <div className="flex items-center">
                    <Label htmlFor="password">Password</Label>
                    <a
                      href="#"
                      className="ml-auto text-sm underline-offset-4 hover:underline"
                    >
                      Forgot your password?
                    </a>
                  </div>
                  <PasswordInput
                    id="password"
                    label=""
                    placeholder="Enter your password"
                    value={formData.password}
                    onChange={handlePasswordChange}
                    showStrength={false}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? "Signing in..." : "Sign in"}
                </Button>
              </div>
              <div className="text-center text-sm">
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={onShowRegistration}
                  className="underline underline-offset-4 hover:text-primary"
                >
                  Sign up
                </button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
      <div className="text-balance text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4 [&_a]:hover:text-primary">
        By clicking continue, you agree to our <a href="#">Terms of Service</a>{" "}
        and <a href="#">Privacy Policy</a>.
      </div>
    </div>
  )
}
