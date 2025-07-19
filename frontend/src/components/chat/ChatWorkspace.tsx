import React, { useEffect, useRef, useCallback } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useParams } from "react-router-dom"
import { RootState, AppDispatch } from "../../store/store"
import {
  setMessages,
  setCurrentConversation,
  setConnectionStatus,
  handleStreamingUpdate,
} from "../../store/slices/chatSlice"
import MessageList from "../chat/MessageList"
import MessageInput from "../chat/MessageInput"
import ChatWebSocket from "../../services/ChatWebSocket"

const ChatWorkspace: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const { conversationId } = useParams<{ conversationId: string }>()
  const wsRef = useRef<ChatWebSocket | null>(null)

  const { currentConversationId, messages, connectionStatus, isStreaming } =
    useSelector((state: RootState) => state.chat)

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
      }
    }
  }, [conversationId, dispatch, loadConversationMessages])

  const handleSendMessage = (content: string) => {
    if (wsRef.current && currentConversationId) {
      wsRef.current.sendMessage(content)
    }
  }

  const currentMessages = conversationId ? messages[conversationId] || [] : []

  if (!conversationId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a8.96 8.96 0 01-4.906-1.426L3 21l2.426-5.094A8.96 8.96 0 013 12a8 8 0 018-8c4.418 0 8 3.582 8 8z"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">
            Welcome to Chat
          </h2>
          <p className="text-gray-600 mb-6">
            Select a conversation or start a new one to chat with multiple AI
            providers
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

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={currentMessages} isStreaming={isStreaming} />
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

export default ChatWorkspace
