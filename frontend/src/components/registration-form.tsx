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

interface RegistrationFormProps extends React.ComponentProps<"div"> {
  onShowLogin?: () => void
}

export function RegistrationForm({
  className,
  onShowLogin,
  ...props
}: RegistrationFormProps) {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.firstName.trim()) {
      newErrors.firstName = "First name is required"
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = "Last name is required"
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address"
    }

    if (!formData.password) {
      newErrors.password = "Password is required"
    } else {
      // Password strength validation
      const passwordRequirements = [
        {
          regex: /.{8,}/,
          message: "Password must be at least 8 characters long",
        },
        { regex: /[0-9]/, message: "Password must contain at least 1 number" },
        {
          regex: /[a-z]/,
          message: "Password must contain at least 1 lowercase letter",
        },
        {
          regex: /[A-Z]/,
          message: "Password must contain at least 1 uppercase letter",
        },
      ]

      const unmetRequirements = passwordRequirements.filter(
        (req) => !req.regex.test(formData.password)
      )
      if (unmetRequirements.length > 0) {
        newErrors.password = unmetRequirements[0].message
      }
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password"
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    setErrors({})

    try {
      const response = await fetch("http://localhost:8013/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: formData.email,
          first_name: formData.firstName,
          last_name: formData.lastName,
          password: formData.password,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        // Registration successful, automatically log in
        await login(data.access_token, data.refresh_token)
        navigate(ROUTES.WELCOME)
      } else {
        setErrors({ submit: data.detail || "Registration failed" })
      }
    } catch (error) {
      setErrors({ submit: "Network error. Please try again." })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Create an account</CardTitle>
          <CardDescription>
            Enter your information to create an account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col gap-6">
              <div className="grid gap-2">
                <Label htmlFor="firstName">First name</Label>
                <Input
                  id="firstName"
                  name="firstName"
                  type="text"
                  placeholder="John"
                  value={formData.firstName}
                  onChange={handleChange}
                  required
                />
                {errors.firstName && (
                  <span className="text-sm text-red-500">
                    {errors.firstName}
                  </span>
                )}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="lastName">Last name</Label>
                <Input
                  id="lastName"
                  name="lastName"
                  type="text"
                  placeholder="Doe"
                  value={formData.lastName}
                  onChange={handleChange}
                  required
                />
                {errors.lastName && (
                  <span className="text-sm text-red-500">
                    {errors.lastName}
                  </span>
                )}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="john@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
                {errors.email && (
                  <span className="text-sm text-red-500">{errors.email}</span>
                )}
              </div>
              <PasswordInput
                id="password"
                label="Password"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handlePasswordChange}
                required
                error={errors.password}
              />
              <div className="grid gap-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                />
                {errors.confirmPassword && (
                  <span className="text-sm text-red-500">
                    {errors.confirmPassword}
                  </span>
                )}
              </div>
              {errors.submit && (
                <div className="text-sm text-red-500 text-center">
                  {errors.submit}
                </div>
              )}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Creating account..." : "Create account"}
              </Button>
              <div className="text-center text-sm">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={onShowLogin}
                  className="underline underline-offset-4 hover:text-primary"
                >
                  Sign in
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
