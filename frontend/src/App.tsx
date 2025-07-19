import React from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import MainLayout from "./components/layout/MainLayout"
import ResearchWorkspace from "./components/research/ResearchWorkspace"
import ProjectsView from "./components/projects/ProjectsView"
import HealthDashboard from "./components/health/HealthDashboard"
import TaskViewer from "./components/tasks/TaskViewer"
import DebugUI from "./components/debug/DebugUI"

function App() {
  return (
    <div className="h-screen bg-gray-50">
      <MainLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/research" element={<ResearchWorkspace />} />
          <Route path="/research/:sessionId" element={<ResearchWorkspace />} />
          <Route path="/projects" element={<ProjectsView />} />
          <Route path="/health" element={<HealthDashboard />} />
          <Route path="/tasks" element={<TaskViewer />} />
          <Route path="/debug" element={<DebugUI />} />
        </Routes>
      </MainLayout>
    </div>
  )
}

export default App
