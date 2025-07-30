import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import Layout from "./components/layout/Layout"
import WelcomePage from "./components/welcome/WelcomePage"
import AuthPage from "./components/auth/AuthPage"
import { TwoFactorSetup } from "./components/TwoFactorSetup"
import { UserProfile } from "./components/UserProfile"
import { SystemHealth } from "./components/SystemHealth"
import { ProjectManagement } from "./components/ProjectManagement"
import { ProjectDetails } from "./components/ProjectDetails"
import { ProtectedRoute } from "./components/auth/ProtectedRoute"
import { useAuth } from "./hooks/useAuth"
import { ROUTES } from "./utils/routes"

function App() {
  const { isAuthenticated } = useAuth()

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route
          path={ROUTES.AUTH}
          element={
            isAuthenticated ? (
              <Navigate to={ROUTES.WELCOME} replace />
            ) : (
              <AuthPage />
            )
          }
        />
        <Route
          path={ROUTES.LOGIN}
          element={<Navigate to={ROUTES.AUTH} replace />}
        />
        <Route
          path={ROUTES.REGISTER}
          element={<Navigate to={ROUTES.AUTH} replace />}
        />

        {/* Development-only test route (bypasses auth) */}
        <Route path="/test-projects" element={
          <Layout>
            <ProjectManagement />
          </Layout>
        } />
        <Route path="/test-projects/:id" element={
          <Layout>
            <ProjectDetails />
          </Layout>
        } />

        {/* Development-only test route for welcome page */}
        <Route
          path="/test-welcome"
          element={
            <Layout>
              <Routes>
                <Route path="/" element={<WelcomePage />} />
              </Routes>
            </Layout>
          }
        />

        {/* Protected routes */}
        <Route
          path="*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route
                    path={ROUTES.HOME}
                    element={<Navigate to={ROUTES.WELCOME} replace />}
                  />
                  <Route path={ROUTES.WELCOME} element={<WelcomePage />} />
                  <Route path={ROUTES.PROJECTS} element={<ProjectManagement />} />
                  <Route path={ROUTES.PROJECT_DETAILS} element={<ProjectDetails />} />
                  <Route path={ROUTES.PROFILE} element={<UserProfile />} />
                  <Route
                    path={ROUTES.SYSTEM_HEALTH}
                    element={<SystemHealth />}
                  />
                  <Route
                    path={ROUTES.TWO_FACTOR}
                    element={<TwoFactorSetup />}
                  />
                  {/* Future protected routes can be added here */}
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
