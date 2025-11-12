import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import MessageList from './MessageList'

function ChatInterface({ uploadedFile, apiBaseUrl }) {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Add welcome message when file is uploaded
    if (uploadedFile) {
      const welcomeMessage = {
        role: 'assistant',
        content: `File "${uploadedFile.filename}" uploaded successfully! I can help you analyze this Excel file. Try asking me to:\n\n- Analyze the data statistics\n- Compare columns\n- Check for data quality issues\n- Create pivot tables\n- Generate charts\n- Detect trends or anomalies\n\nWhat would you like to know?`,
        timestamp: new Date().toISOString()
      }
      setMessages([welcomeMessage])
    }
  }, [uploadedFile])

  const handleSendMessage = async (e) => {
    e.preventDefault()

    if (!inputMessage.trim()) {
      return
    }

    if (!uploadedFile) {
      alert('Please upload an Excel file first')
      return
    }

    // Add user message
    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setSending(true)

    try {
      const response = await axios.post(`${apiBaseUrl}/chat`, {
        message: inputMessage,
        file_path: uploadedFile.file_path,
        conversation_history: messages
      })

      // Add assistant response
      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: response.data.timestamp
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      console.error('Error sending message:', error)

      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || 'Failed to get response from server'}`,
        timestamp: new Date().toISOString(),
        isError: true
      }

      setMessages(prev => [...prev, errorMessage])

    } finally {
      setSending(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  const clearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      setMessages([])
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm flex flex-col h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
            {uploadedFile && (
              <p className="text-sm text-gray-500">
                Analyzing: {uploadedFile.filename}
              </p>
            )}
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Clear Chat
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <svg
                className="mx-auto h-12 w-12 text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="text-lg font-medium mb-2">No messages yet</p>
              <p className="text-sm">
                {uploadedFile
                  ? 'Start a conversation about your Excel file'
                  : 'Upload an Excel file to get started'}
              </p>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} />
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 px-6 py-4">
        <form onSubmit={handleSendMessage} className="flex space-x-4">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              uploadedFile
                ? 'Ask a question about your Excel file...'
                : 'Upload a file first...'
            }
            disabled={!uploadedFile || sending}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            rows="2"
          />

          <button
            type="submit"
            disabled={!uploadedFile || !inputMessage.trim() || sending}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              uploadedFile && inputMessage.trim() && !sending
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {sending ? (
              <svg
                className="animate-spin h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              'Send'
            )}
          </button>
        </form>

        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

export default ChatInterface
