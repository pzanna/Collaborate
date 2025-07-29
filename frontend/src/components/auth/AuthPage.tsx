import { useState } from "react"
import { Brain } from "lucide-react"
import { LoginForm } from "@/components/login-form"
import { RegistrationForm } from "@/components/registration-form"

export default function AuthPage() {
  const [showRegistration, setShowRegistration] = useState(false)

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex items-center gap-2 self-center font-medium">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Brain className="size-4" />
          </div>
          <span className="text-lg font-semibold">Eunice Research</span>
        </div>

        {showRegistration ? (
          <RegistrationForm onShowLogin={() => setShowRegistration(false)} />
        ) : (
          <LoginForm onShowRegistration={() => setShowRegistration(true)} />
        )}
      </div>
    </div>
  )
}
