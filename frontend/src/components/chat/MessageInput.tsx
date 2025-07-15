import React, { useState, KeyboardEvent } from "react"
import { PaperAirplaneIcon, PlusIcon } from "@heroicons/react/24/outline"

interface MessageInputProps {
  onSendMessage: (content: string) => void
  disabled?: boolean
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled = false,
}) => {
  const [message, setMessage] = useState("")

  const handleSubmit = () => {
    const trimmedMessage = message.trim()
    if (trimmedMessage && !disabled) {
      onSendMessage(trimmedMessage)
      setMessage("")
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-end space-x-3">
        {/* Attachment button */}
        <button
          className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 transition-colors"
          title="Attach file"
        >
          <PlusIcon className="h-5 w-5" />
        </button>

        {/* Message input */}
        <div className="flex-1">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask both AIs, or @mention specific provider..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={1}
            disabled={disabled}
            style={{
              minHeight: "40px",
              maxHeight: "120px",
              resize: "none",
            }}
          />
          <div className="mt-1 text-xs text-gray-500">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>

        {/* Send button */}
        <button
          onClick={handleSubmit}
          disabled={disabled || !message.trim()}
          className={`flex-shrink-0 p-2 rounded-lg transition-colors ${
            disabled || !message.trim()
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-blue-500 text-white hover:bg-blue-600"
          }`}
          title="Send message"
        >
          <PaperAirplaneIcon className="h-5 w-5" />
        </button>
      </div>

      {/* AI mention suggestions */}
      {message.includes("@") && (
        <div className="mt-2 p-2 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-600 mb-1">Available AIs:</div>
          <div className="flex space-x-2">
            <button
              onClick={() => setMessage(message + "openai ")}
              className="px-2 py-1 bg-white border rounded text-xs hover:bg-gray-100"
            >
              @openai
            </button>
            <button
              onClick={() => setMessage(message + "xai ")}
              className="px-2 py-1 bg-white border rounded text-xs hover:bg-gray-100"
            >
              @xai
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default MessageInput
