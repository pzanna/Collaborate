import React, { useState } from "react"
import { ResearchTask } from "../../../store/slices/chatSlice"

interface ResearchResultsProps {
  task: ResearchTask
  className?: string
}

const ResearchResults: React.FC<ResearchResultsProps> = ({
  task,
  className = "",
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null)

  if (!task.results) {
    return null
  }

  const {
    search_results,
    reasoning_output,
    execution_results,
    synthesis,
    metadata,
  } = task.results

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section)
  }

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}
    >
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            Research Results
          </h3>
          <span className="text-sm text-gray-500">
            Completed {new Date(task.updated_at).toLocaleString()}
          </span>
        </div>
        <p className="text-sm text-gray-600 mt-1 italic">"{task.query}"</p>
      </div>

      <div className="divide-y divide-gray-200">
        {/* Search Results */}
        {search_results && search_results.length > 0 && (
          <div className="p-4">
            <button
              onClick={() => toggleSection("search")}
              className="flex items-center justify-between w-full text-left"
            >
              <h4 className="text-sm font-medium text-gray-900 flex items-center">
                🔍 Search Results
                <span className="ml-2 text-xs text-gray-500">
                  ({search_results.length} items)
                </span>
              </h4>
              <span className="text-sm text-gray-400">
                {expandedSection === "search" ? "⬆️" : "⬇️"}
              </span>
            </button>

            {expandedSection === "search" && (
              <div className="mt-3 space-y-3">
                {search_results.map((result: any, index: number) => (
                  <div key={index} className="bg-gray-50 p-3 rounded border">
                    <div className="flex items-start justify-between">
                      <h5 className="text-sm font-medium text-gray-900 flex-1">
                        {result.url ? (
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 hover:underline"
                          >
                            {result.title}
                          </a>
                        ) : (
                          result.title
                        )}
                      </h5>
                      {result.relevance_score && (
                        <span className="text-xs text-gray-500 ml-2">
                          {Math.round(result.relevance_score * 100)}%
                        </span>
                      )}
                    </div>

                    {result.snippet && (
                      <p className="text-sm text-gray-600 mt-1">
                        {result.snippet}
                      </p>
                    )}

                    {result.url && (
                      <p className="text-xs text-gray-500 mt-2 truncate">
                        {result.url}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Reasoning Output */}
        {reasoning_output && (
          <div className="p-4">
            <button
              onClick={() => toggleSection("reasoning")}
              className="flex items-center justify-between w-full text-left"
            >
              <h4 className="text-sm font-medium text-gray-900">
                🧠 Analysis & Reasoning
              </h4>
              <span className="text-sm text-gray-400">
                {expandedSection === "reasoning" ? "⬆️" : "⬇️"}
              </span>
            </button>

            {expandedSection === "reasoning" && (
              <div className="mt-3 bg-gray-50 p-3 rounded border">
                <div className="text-sm text-gray-700 whitespace-pre-wrap">
                  {reasoning_output}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Execution Results */}
        {execution_results && execution_results.length > 0 && (
          <div className="p-4">
            <button
              onClick={() => toggleSection("execution")}
              className="flex items-center justify-between w-full text-left"
            >
              <h4 className="text-sm font-medium text-gray-900 flex items-center">
                ⚡ Execution Results
                <span className="ml-2 text-xs text-gray-500">
                  ({execution_results.length} items)
                </span>
              </h4>
              <span className="text-sm text-gray-400">
                {expandedSection === "execution" ? "⬆️" : "⬇️"}
              </span>
            </button>

            {expandedSection === "execution" && (
              <div className="mt-3 space-y-2">
                {execution_results.map((result: any, index: number) => (
                  <div key={index} className="bg-gray-50 p-3 rounded border">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Synthesis */}
        {synthesis && (
          <div className="p-4">
            <button
              onClick={() => toggleSection("synthesis")}
              className="flex items-center justify-between w-full text-left"
            >
              <h4 className="text-sm font-medium text-gray-900">
                📝 Summary & Synthesis
              </h4>
              <span className="text-sm text-gray-400">
                {expandedSection === "synthesis" ? "⬆️" : "⬇️"}
              </span>
            </button>

            {expandedSection === "synthesis" && (
              <div className="mt-3 bg-blue-50 p-4 rounded border border-blue-200">
                <div className="text-sm text-gray-800 whitespace-pre-wrap">
                  {synthesis}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Metadata */}
        {metadata && Object.keys(metadata).length > 0 && (
          <div className="p-4">
            <button
              onClick={() => toggleSection("metadata")}
              className="flex items-center justify-between w-full text-left"
            >
              <h4 className="text-sm font-medium text-gray-900">📊 Metadata</h4>
              <span className="text-sm text-gray-400">
                {expandedSection === "metadata" ? "⬆️" : "⬇️"}
              </span>
            </button>

            {expandedSection === "metadata" && (
              <div className="mt-3 bg-gray-50 p-3 rounded border">
                <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                  {JSON.stringify(metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResearchResults
