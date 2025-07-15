import React from "react"
import { Routes, Route } from "react-router-dom"
import ChatLayout from "./components/layout/ChatLayout"
import ConversationView from "./components/chat/ConversationView"
import ProjectsView from "./components/projects/ProjectsView"
import HealthDashboard from "./components/health/HealthDashboard"

function App() {
  return (
    <div className="h-screen bg-gray-50">
      <ChatLayout>
        <Routes>
          <Route path="/" element={<ConversationView />} />
          <Route
            path="/conversation/:conversationId"
            element={<ConversationView />}
          />
          <Route path="/projects" element={<ProjectsView />} />
          <Route path="/health" element={<HealthDashboard />} />
        </Routes>
      </ChatLayout>
    </div>
  )
}

export default App
