import React, { useEffect, useRef, useCallback } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useParams } from "react-router-dom"
import { RootState, AppDispatch } from "../../store/store"
import {
  setMessages,
  setCurrentConversation,
  setConnectionStatus,
  setResearchConnectionStatus,
  handleStreamingUpdate,
  handleResearchProgress,
} from "../../store/slices/chatSlice"
import MessageList from "./MessageList"
import MessageInput from "./MessageInput"
import ChatWebSocket from "../../services/ChatWebSocket"
import ResearchWebSocket from "../../services/ResearchWebSocket"
import ResearchModeIndicator from "./research/ResearchModeIndicator"
import ResearchProgress from "./research/ResearchProgress"
import ResearchTaskList from "./research/ResearchTaskList"
import ResearchInput from "./research/ResearchInput"

const ConversationView: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const { conversationId } = useParams<{ conversationId: string }>()
  const wsRef = useRef<ChatWebSocket | null>(null)
  const researchWsRef = useRef<ResearchWebSocket | null>(null)

  const {
    currentConversationId,
    messages,
    connectionStatus,
    researchConnectionStatus,
    isStreaming,
    isResearchMode,
    activeResearchTask,
    researchTasks,
  } = useSelector((state: RootState) => state.chat)

  const loadConversationMessages = useCallback(
    async (convId: string) => {
      try {
        const response = await fetch(`/api/conversations/${convId}/messages`)
        if (response.ok) {
          const messages = await response.json()
          dispatch(setMessages({ conversationId: convId, messages }))
        }
      } catch (error) {
        console.error("Failed to load messages:", error)
      }
    },
    [dispatch]
  )

  useEffect(() => {
    if (conversationId) {
      dispatch(setCurrentConversation(conversationId))
      loadConversationMessages(conversationId)

      // Initialize WebSocket connection for real-time updates
      if (wsRef.current) {
        wsRef.current.disconnect()
      }

      const newWs = new ChatWebSocket(
        conversationId,
        (update) => dispatch(handleStreamingUpdate(update)),
        (status) => dispatch(setConnectionStatus(status))
      )
      wsRef.current = newWs
      newWs.connect()

      // Return cleanup function that captures the WebSocket instance
      return () => {
        if (newWs) {
          newWs.disconnect()
        }
        if (researchWsRef.current) {
          researchWsRef.current.disconnect()
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, dispatch, loadConversationMessages])

  const handleSendMessage = (content: string) => {
    if (wsRef.current && currentConversationId) {
      wsRef.current.sendMessage(content)
    }
  }

  const handleResearchStarted = (taskId: string) => {
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
  }

  const currentMessages = conversationId ? messages[conversationId] || [] : []
  const currentResearchTasks = conversationId
    ? researchTasks[conversationId] || []
    : []

  if (!conversationId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Welcome to Collaborate AI
          </h2>
          <p className="text-gray-600 mb-6">
            Select a conversation or start a new one to begin chatting with
            multiple AI providers
          </p>
          <div className="flex items-center justify-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">AI</span>
              </div>
              <span className="text-sm text-gray-600">OpenAI</span>
            </div>
            <span className="text-gray-400">+</span>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">X</span>
              </div>
              <span className="text-sm text-gray-600">xAI</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Connection status bar */}
      {connectionStatus !== "connected" && (
        <div
          className={`px-4 py-2 text-sm text-center ${
            connectionStatus === "connecting"
              ? "bg-yellow-100 text-yellow-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {connectionStatus === "connecting"
            ? "Connecting to chat server..."
            : "Connection lost. Attempting to reconnect..."}
        </div>
      )}

      {/* Research mode indicator */}
      {isResearchMode && <ResearchModeIndicator className="mx-4 mt-4" />}

      {/* Research progress */}
      {activeResearchTask && <ResearchProgress className="mx-4 mt-2" />}

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={currentMessages} isStreaming={isStreaming} />
      </div>

      {/* Research tasks */}
      {currentResearchTasks.length > 0 && (
        <div className="border-t border-gray-200 bg-gray-50 p-4 max-h-80 overflow-y-auto">
          <ResearchTaskList conversationId={conversationId!} />
        </div>
      )}

      {/* Research input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <ResearchInput
          conversationId={conversationId!}
          onResearchStarted={handleResearchStarted}
          className="mb-4"
        />
      </div>

      {/* Message input */}
      <div className="border-t border-gray-200 bg-white">
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={connectionStatus !== "connected" || isStreaming}
        />
      </div>
    </div>
  )
}

export default ConversationView
