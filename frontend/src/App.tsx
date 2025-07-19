import React from "react"
import { Routes, Route } from "react-router-dom"
import MainLayout from "./components/layout/MainLayout"
import ChatWorkspace from "./components/chat/ChatWorkspace"
import ResearchWorkspace from "./components/research/ResearchWorkspace"
import ProjectsView from "./components/projects/ProjectsView"
import HealthDashboard from "./components/health/HealthDashboard"

function App() {
  return (
    <div className="h-screen bg-gray-50">
      <MainLayout>
        <Routes>
          <Route path="/" element={<ChatWorkspace />} />
          <Route path="/chat" element={<ChatWorkspace />} />
          <Route path="/chat/:conversationId" element={<ChatWorkspace />} />
          <Route path="/research" element={<ResearchWorkspace />} />
          <Route path="/research/:sessionId" element={<ResearchWorkspace />} />
          <Route path="/projects" element={<ProjectsView />} />
          <Route path="/health" element={<HealthDashboard />} />
        </Routes>
      </MainLayout>
    </div>
  )
}

export default App
