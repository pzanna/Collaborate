import React, { useState } from "react"
import { useDispatch } from "react-redux"
import { AppDispatch } from "../../../store/store"
import { startResearchTask } from "../../../store/slices/chatSlice"

interface ResearchInputProps {
  conversationId: string
  onResearchStarted?: (taskId: string) => void
  className?: string
}

const ResearchInput: React.FC<ResearchInputProps> = ({
  conversationId,
  onResearchStarted,
  className = "",
}) => {
  const dispatch = useDispatch<AppDispatch>()
  const [query, setQuery] = useState("")
  const [researchMode, setResearchMode] = useState<
    "comprehensive" | "quick" | "deep"
  >("comprehensive")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!query.trim()) return

    setIsLoading(true)

    try {
      const result = await dispatch(
        startResearchTask({
          conversationId,
          query: query.trim(),
          researchMode,
        })
      ).unwrap()

      if (onResearchStarted) {
        onResearchStarted(result.task_id)
      }

      setQuery("")
    } catch (error) {
      console.error("Failed to start research task:", error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}
    >
      <div className="p-4">
        <div className="flex items-center space-x-2 mb-3">
          <span className="text-lg">🔬</span>
          <h3 className="text-sm font-medium text-gray-900">
            Start Research Task
          </h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label
              htmlFor="research-query"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Research Query
            </label>
            <textarea
              id="research-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your research question or topic..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              disabled={isLoading}
            />
          </div>

          <div>
            <label
              htmlFor="research-mode"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Research Mode
            </label>
            <select
              id="research-mode"
              value={researchMode}
              onChange={(e) =>
                setResearchMode(
                  e.target.value as "comprehensive" | "quick" | "deep"
                )
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isLoading}
            >
              <option value="comprehensive">
                Comprehensive - Thorough research across multiple sources
              </option>
              <option value="quick">
                Quick - Fast overview with key findings
              </option>
              <option value="deep">
                Deep - In-depth analysis with detailed reasoning
              </option>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-xs text-gray-500">
              {researchMode === "comprehensive" &&
                "Estimated time: 2-5 minutes"}
              {researchMode === "quick" && "Estimated time: 30-60 seconds"}
              {researchMode === "deep" && "Estimated time: 5-10 minutes"}
            </div>

            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                !query.trim() || isLoading
                  ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              }`}
            >
              {isLoading ? (
                <span className="flex items-center space-x-2">
                  <span className="animate-spin">🔄</span>
                  <span>Starting...</span>
                </span>
              ) : (
                "Start Research"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ResearchInput
