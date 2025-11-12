import { useState } from 'react'

function ThinkingSteps({ steps }) {
  const [isExpanded, setIsExpanded] = useState(false)

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

  // Get icon for step type
  const getStepIcon = (type) => {
    switch (type) {
      case 'thinking_start':
        return '🔍'
      case 'tool_start':
        return '⚙️'
      case 'tool_complete':
        return '✓'
      case 'tool_error':
        return '✗'
      case 'thinking':
        return '💭'
      default:
        return '•'
    }
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

  // Get step display text
  const getStepText = (step) => {
    switch (step.type) {
      case 'thinking_start':
        return step.message || 'Starting analysis...'
      case 'tool_start':
        return `${formatToolName(step.tool_name)}...`
      case 'tool_complete':
        return `${formatToolName(step.tool_name)} - ${step.summary || 'Completed'}`
      case 'tool_error':
        return `${formatToolName(step.tool_name)} - Error: ${step.error}`
      case 'thinking':
        return step.message || 'Processing...'
      default:
        return JSON.stringify(step)
    }
  }

  return (
    <div className="mb-3 text-sm">
      {/* Collapsed summary */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
      >
        <span className="text-base">🔍</span>
        <span className="font-medium">{getSummary()}</span>
        <span className="text-xs text-gray-400">
          ({isExpanded ? 'collapse' : 'expand'})
        </span>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-2 ml-6 space-y-1 border-l-2 border-gray-200 pl-3">
          {steps.map((step, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 ${
                step.type === 'tool_error' ? 'text-red-600' : 'text-gray-600'
              }`}
            >
              <span className="text-base leading-none mt-0.5">
                {getStepIcon(step.type)}
              </span>
              <span className="flex-1">{getStepText(step)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ThinkingSteps
