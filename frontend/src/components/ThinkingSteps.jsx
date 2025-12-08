import { useState } from 'react'
import { ChevronDown, ChevronRight, Code, AlertCircle, Loader2 } from 'lucide-react'

function CodeBlock({ code, title }) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  if (!code || Object.keys(code).length === 0) return null
  
  const formattedCode = JSON.stringify(code, null, 2)
  
  return (
    <div className="mt-1 ml-5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Code className="h-3 w-3" />
        <span>{title}</span>
      </button>
      {isExpanded && (
        <pre className="mt-1 p-2 bg-gray-900 text-gray-100 rounded-md text-xs overflow-x-auto max-h-48 overflow-y-auto">
          <code>{formattedCode}</code>
        </pre>
      )}
    </div>
  )
}

function ThinkingSteps({ steps }) {
  // Auto-expand if there are errors to show transparency
  const hasErrors = steps && steps.some(s => s.type === 'tool_error')
  const [isExpanded, setIsExpanded] = useState(hasErrors)

  if (!steps || steps.length === 0) {
    return null
  }

  // Count tool executions
  const toolCount = steps.filter(s => s.type === 'tool_start').length

  // Get summary message
  const getSummary = () => {
    if (toolCount > 0) {
      return `Used ${toolCount} tool${toolCount !== 1 ? 's' : ''} to analyze data`
    }
    return 'Processing...'
  }

  // Format tool name for display
  const formatToolName = (toolName) => {
    if (!toolName) return ''
    // Convert snake_case to Title Case
    return toolName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Group steps by tool execution
  const groupedSteps = []
  let currentGroup = null

  steps.forEach((step) => {
    if (step.type === 'thinking_start') {
      groupedSteps.push({ type: 'thinking', step })
    } else if (step.type === 'tool_start') {
      currentGroup = { 
        toolName: step.tool_name, 
        input: step.input, 
        status: 'running',
        result: null,
        error: null
      }
    } else if (step.type === 'tool_complete' && currentGroup) {
      currentGroup.status = 'completed'
      currentGroup.result = step.result
      currentGroup.summary = step.summary
      groupedSteps.push({ type: 'tool', ...currentGroup })
      currentGroup = null
    } else if (step.type === 'tool_error' && currentGroup) {
      currentGroup.status = 'error'
      currentGroup.error = step.error
      groupedSteps.push({ type: 'tool', ...currentGroup })
      currentGroup = null
    }
  })

  // Add any in-progress tool
  if (currentGroup) {
    groupedSteps.push({ type: 'tool', ...currentGroup })
  }

  return (
    <div className="mb-3 text-sm">
      {/* Collapsed summary */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
      >
        <span className="material-symbols-rounded text-base">function</span>
        <span className="font-medium">{getSummary()}</span>
        <span className="text-xs text-gray-400">
          {isExpanded ? <ChevronDown className="h-3 w-3 inline" /> : <ChevronRight className="h-3 w-3 inline" />}
        </span>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-2 ml-4 space-y-2">
          {groupedSteps.map((group, index) => (
            <div key={index}>
              {group.type === 'thinking' && (
                <div className="flex items-center gap-2 text-gray-500 text-xs">
                  <span className="material-symbols-rounded text-sm">psychology</span>
                  <span>{group.step.message || 'Analyzing...'}</span>
                </div>
              )}
              {group.type === 'tool' && (
                <div className="border border-gray-200 rounded-lg p-2 bg-white">
                  <div className="flex items-center gap-2">
                    {group.status === 'running' && (
                      <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                    )}
                    {group.status === 'completed' && (
                      <span className="material-symbols-rounded text-green-500 text-base">check_circle</span>
                    )}
                    {group.status === 'error' && (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="font-medium text-gray-700">
                      {formatToolName(group.toolName)}
                    </span>
                    {group.summary && (
                      <span className="text-xs text-gray-500">— {group.summary}</span>
                    )}
                  </div>
                  
                  {/* Code blocks */}
                  {group.input && Object.keys(group.input).length > 0 && (
                    <CodeBlock code={group.input} title="Input Parameters" />
                  )}
                  {group.result && (
                    <CodeBlock code={group.result} title="Output" />
                  )}
                  {group.error && (
                    <div className="mt-1 ml-5 p-2 bg-red-50 text-red-700 rounded text-xs">
                      Error: {group.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ThinkingSteps
