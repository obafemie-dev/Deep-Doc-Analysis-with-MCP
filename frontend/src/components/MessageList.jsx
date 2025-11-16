import ThinkingSteps from './ThinkingSteps'
import FeedbackButtons from './FeedbackButtons'

function MessageList({ messages }) {
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''

    const date = new Date(timestamp)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  }

  const formatContent = (content) => {
    // Basic markdown-like formatting
    // Convert **bold** to <strong>
    let formatted = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')

    // Convert line breaks to <br>
    formatted = formatted.replace(/\n/g, '<br>')

    return formatted
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <div
          key={message.id || message.timestamp || Math.random()}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-3 ${
              message.role === 'user'
                ? 'bg-[#5219281A] text-[#521928]'
                : message.isError
                ? 'bg-red-50 border border-red-200 text-red-800'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            {/* Message Header */}
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-semibold opacity-75">
                {message.role === 'user' ? 'You' : 'Assistant'}
              </span>
              {message.timestamp && (
                <>
                  <span className="text-xs opacity-50">•</span>
                  <span className="text-xs opacity-75">
                    {formatTimestamp(message.timestamp)}
                  </span>
                </>
              )}
            </div>

            {/* Chain of Thought - Show thinking steps for assistant messages */}
            {message.role === 'assistant' && message.thinking_steps && message.thinking_steps.length > 0 && (
              <ThinkingSteps steps={message.thinking_steps} />
            )}

            {/* Message Content */}
            <div
              className="text-sm whitespace-pre-wrap"
              dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
            />

            {/* Feedback Buttons - Only for assistant messages */}
            {message.role === 'assistant' && !message.isError && message.content && (
              <FeedbackButtons
                messageId={String(message.id || message.timestamp || Date.now())}
                queryEventId={null}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default MessageList
