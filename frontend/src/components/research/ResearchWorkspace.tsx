import React, { useEffect, useRef, useCallback } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useParams } from "react-router-dom"
import { RootState, AppDispatch } from "../../store/store"
import {
  setCurrentConversation,
  setResearchConnectionStatus,
  handleResearchProgress,
} from "../../store/slices/chatSlice"
import ResearchWebSocket from "../../services/ResearchWebSocket"
import ResearchModeIndicator from "../chat/research/ResearchModeIndicator"
import ResearchProgress from "../chat/research/ResearchProgress"
import ResearchTaskList from "../chat/research/ResearchTaskList"
import ResearchInput from "../chat/research/ResearchInput"
import ResearchResults from "../chat/research/ResearchResults"

const ResearchWorkspace: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const { sessionId } = useParams<{ sessionId: string }>()
  const researchWsRef = useRef<ResearchWebSocket | null>(null)

  const { researchConnectionStatus, activeResearchTask, researchTasks } =
    useSelector((state: RootState) => state.chat)

  const handleResearchStarted = useCallback(
    (taskId: string) => {
      // Create research WebSocket connection for this task
      if (researchWsRef.current) {
        researchWsRef.current.disconnect()
      }

      const newResearchWs = new ResearchWebSocket(
        taskId,
        (update) => dispatch(handleResearchProgress(update)),
        (status) => dispatch(setResearchConnectionStatus(status))
      )

      researchWsRef.current = newResearchWs
      newResearchWs.connect()
    },
    [dispatch]
  )

  useEffect(() => {
    if (sessionId) {
      dispatch(setCurrentConversation(sessionId))
    }

    return () => {
      if (researchWsRef.current) {
        researchWsRef.current.disconnect()
      }
    }
  }, [sessionId, dispatch])

  const currentResearchTasks = sessionId ? researchTasks[sessionId] || [] : []

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Research Workspace
          </h2>
          <p className="text-gray-600 mb-6">
            Start a new research session to explore topics with AI assistance
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Connection status bar */}
      {researchConnectionStatus !== "connected" && (
        <div
          className={`px-4 py-2 text-sm text-center ${
            researchConnectionStatus === "connecting"
              ? "bg-yellow-100 text-yellow-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {researchConnectionStatus === "connecting"
            ? "Connecting to research server..."
            : "Research connection lost. Attempting to reconnect..."}
        </div>
      )}

      {/* Research mode indicator */}
      <ResearchModeIndicator className="mx-4 mt-4" />

      {/* Research progress */}
      {activeResearchTask && <ResearchProgress className="mx-4 mt-2" />}

      {/* Main research area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Research tasks panel */}
        <div className="w-1/3 border-r border-gray-200 bg-white p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Tasks</h3>
          <ResearchTaskList conversationId={sessionId} />
        </div>

        {/* Results panel */}
        <div className="flex-1 bg-gray-50 p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Results</h3>
          <ResearchResults tasks={currentResearchTasks} />
        </div>
      </div>

      {/* Research input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <ResearchInput
          conversationId={sessionId}
          onResearchStarted={handleResearchStarted}
        />
      </div>
    </div>
  )
}

export default ResearchWorkspace
