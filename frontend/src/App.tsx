import React from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import MainLayout from "./components/layout/MainLayout"
import ResearchWorkspace from "./components/research/ResearchWorkspace"
import ProjectsView from "./components/projects/ProjectsView"
import ProjectDetailView from "./components/projects/ProjectDetailView"
import ResearchTaskDetailView from "./components/research/ResearchTaskDetailView"
import ResearchTopicList from "./components/research/ResearchTopicList"
import ResearchTopicDetail from "./components/research/ResearchTopicDetail"
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
          <Route
            path="/research/task/:taskId"
            element={<ResearchTaskDetailView />}
          />
          <Route path="/projects" element={<ProjectsView />} />
          <Route path="/projects/:projectId" element={<ProjectDetailView />} />

          {/* Hierarchical Research Routes */}
          <Route
            path="/projects/:projectId/topics"
            element={<ResearchTopicList />}
          />
          <Route
            path="/projects/:projectId/topics/:topicId"
            element={<ResearchTopicDetail />}
          />

          <Route path="/health" element={<HealthDashboard />} />
          <Route path="/tasks" element={<TaskViewer />} />
          <Route path="/debug" element={<DebugUI />} />
        </Routes>
      </MainLayout>
    </div>
  )
}

export default App
