import { useAuth } from "@/hooks/useAuth"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ROUTES } from "@/utils/routes"

export function WelcomePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome to Eunice!</CardTitle>
          <CardDescription>You have successfully logged in.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {user && (
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Welcome back,</p>
              <p className="font-medium">
                {user.first_name && user.last_name
                  ? `${user.first_name} ${user.last_name}`
                  : user.email}
              </p>
              <p className="text-sm text-muted-foreground">{user.email}</p>
            </div>
          )}

          <div className="space-y-2">
            <p className="text-sm text-center text-muted-foreground">
              This is your dashboard. From here you can access all of Eunice's
              features.
            </p>
          </div>

          <div className="space-y-2">
            <Button
              onClick={() => navigate(ROUTES.PROJECTS)}
              variant="default"
              className="w-full"
            >
              View Projects
            </Button>

            {!user?.is_2fa_enabled ? (
              <Button
                onClick={() => navigate(ROUTES.TWO_FACTOR)}
                variant="outline"
                className="w-full"
              >
                Setup Two-Factor Authentication
              </Button>
            ) : (
              <Button
                onClick={() => navigate(ROUTES.TWO_FACTOR)}
                variant="outline"
                className="w-full"
              >
                Manage Two-Factor Authentication
              </Button>
            )}

            <Button onClick={logout} variant="outline" className="w-full">
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
