import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import Layout from "./components/layout/Layout"
import WelcomePage from "./components/welcome/WelcomePage"
import { ROUTES } from "./utils/routes"

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route
            path={ROUTES.HOME}
            element={<Navigate to={ROUTES.WELCOME} replace />}
          />
          <Route path={ROUTES.WELCOME} element={<WelcomePage />} />
          {/* Future routes can be added here */}
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
