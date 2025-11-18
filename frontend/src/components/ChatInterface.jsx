import { useState, useRef, useEffect } from 'react'
import { flushSync } from 'react-dom'
import axios from 'axios'
import MessageList from './MessageList'
import { useAnalytics } from '../hooks/useAnalytics'
import { 
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTools,
  PromptInputButton
} from '@/components/ai-elements/prompt-input'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { PaperclipIcon, XIcon, ArrowUp } from 'lucide-react'

function ChatInterface({ uploadedFile, apiBaseUrl, onClearChat, onFileUpload }) {
  const { sessionId, trackQuery, trackResponse, trackClearChat } = useAnalytics()
  const [messages, setMessages] = useState([])
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const messagesEndRef = useRef(null)
  const welcomeShownForFile = useRef(null)
  const streamingContentRef = useRef('')
  const streamingThinkingRef = useRef([])
  const streamingErrorsRef = useRef([])
  const fileInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Handle file selection
  const handleFileSelect = async (file) => {
    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.ms-excel', // .xls
      'application/vnd.ms-excel.sheet.macroEnabled.12' // .xlsm
    ]

    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls|xlsm)$/i)) {
      setUploadError('Please select a valid Excel file (.xlsx, .xls, .xlsm)')
      setTimeout(() => setUploadError(null), 3000)
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File size must be less than 50MB')
      setTimeout(() => setUploadError(null), 3000)
      return
    }

    setUploadError(null)
    setUploading(true)

    try {
      await onFileUpload(file)
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Error uploading file')
      setTimeout(() => setUploadError(null), 3000)
    } finally {
      setUploading(false)
    }
  }

  const handleAttachmentClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleRemoveFile = () => {
    if (onClearChat) {
      onClearChat()
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (uploadedFile && uploadedFile.file_path !== welcomeShownForFile.current) {
      const welcomeMessage = {
        role: 'assistant',
        content: `File "${uploadedFile.filename}" uploaded successfully! I can help you analyze this Excel file. Try asking me to:\n\n- Analyze the data statistics\n- Compare columns\n- Check for data quality issues\n- Create pivot tables\n- Generate charts\n- Detect trends or anomalies\n\nWhat would you like to know?`,
        timestamp: new Date().toISOString(),
        id: Date.now()
      }
      setMessages([welcomeMessage])
      welcomeShownForFile.current = uploadedFile.file_path
    } else if (!uploadedFile) {
      setMessages([])
      welcomeShownForFile.current = null
    }
  }, [uploadedFile])

  const handleSendMessage = async (userInputMessage) => {
    if (!userInputMessage.trim()) {
      return
    }

    if (!uploadedFile) {
      alert('Please upload an Excel file first')
      return
    }

    const userMessageId = Date.now()
    const userMessage = {
      role: 'user',
      content: userInputMessage,
      timestamp: new Date().toISOString(),
      id: userMessageId
    }

    setMessages(prev => [...prev, userMessage])
    setSending(true)

    // Capture event_id for linking feedback to this query
    const queryEventId = await trackQuery(userInputMessage, uploadedFile?.file_path, messages.length / 2 + 1)

    const assistantMessageId = userMessageId + 1
    const startTime = Date.now()

    streamingContentRef.current = ''
    streamingThinkingRef.current = []
    streamingErrorsRef.current = []

    try {
      const response = await fetch(`${apiBaseUrl}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
        },
        body: JSON.stringify({
          message: userInputMessage,
          file_path: uploadedFile.file_path,
          conversation_history: messages.filter(msg => msg.content && msg.content.trim() !== ''),
          session_id: sessionId
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let chunkNumber = 0

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        chunkNumber++
        const decoded = decoder.decode(value, { stream: true })

        buffer += decoded
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (data === '[DONE]') {
              break
            }

            try {
              const parsed = JSON.parse(data)

              if (parsed.error) {
                console.error('Stream error:', parsed.error)
                streamingErrorsRef.current.push(parsed.error)
                continue
              }

              if (parsed.type === 'content' && parsed.content) {
                streamingContentRef.current += parsed.content

                setMessages(prev => {
                  const existingMessage = prev.find(msg => msg.id === assistantMessageId)
                  if (existingMessage) {
                    // Update existing message
                    return prev.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            content: streamingContentRef.current,
                            thinking_steps: streamingThinkingRef.current
                          }
                        : msg
                    )
                  } else {
                    // Create new assistant message on first content chunk
                    return [...prev, {
                      role: 'assistant',
                      content: streamingContentRef.current,
                      thinking_steps: streamingThinkingRef.current,
                      timestamp: new Date().toISOString(),
                      id: assistantMessageId,
                      queryEventId: queryEventId
                    }]
                  }
                })
              } else if (parsed.type && parsed.type !== 'content') {
                streamingThinkingRef.current = [
                  ...streamingThinkingRef.current,
                  {
                    ...parsed,
                    timestamp: new Date().toISOString()
                  }
                ]

                setMessages(prev => {
                  const existingMessage = prev.find(msg => msg.id === assistantMessageId)
                  if (existingMessage) {
                    // Update existing message
                    return prev.map(msg =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            content: streamingContentRef.current,
                            thinking_steps: streamingThinkingRef.current
                          }
                        : msg
                    )
                  } else {
                    // Create new assistant message if it doesn't exist yet
                    return [...prev, {
                      role: 'assistant',
                      content: streamingContentRef.current,
                      thinking_steps: streamingThinkingRef.current,
                      timestamp: new Date().toISOString(),
                      id: assistantMessageId,
                      queryEventId: queryEventId
                    }]
                  }
                })
              }
            } catch (err) {
              console.error('Error parsing SSE data:', err)
            }
          }
        }
      }

    } catch (error) {
      console.error('Error sending message:', error)

      setMessages(prev => {
        const existingMessage = prev.find(msg => msg.id === assistantMessageId)
        if (existingMessage) {
          return prev.map(msg =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: `Error: ${error.message || 'Failed to get response from server'}`,
                  isError: true
                }
              : msg
          )
        } else {
          // Create error message if assistant message doesn't exist
          return [...prev, {
            role: 'assistant',
            content: `Error: ${error.message || 'Failed to get response from server'}`,
            thinking_steps: [],
            timestamp: new Date().toISOString(),
            id: assistantMessageId,
            queryEventId: queryEventId,
            isError: true
          }]
        }
      })

    } finally {
      setSending(false)

      const responseTime = Date.now() - startTime
      const toolCalls = streamingThinkingRef.current.filter(s => s.type === 'tool_use')
      const responseContent = streamingContentRef.current
      const streamErrors = streamingErrorsRef.current

      if (responseContent.length === 0 && streamErrors.length > 0) {
        setMessages(prev => {
          const existingMessage = prev.find(msg => msg.id === assistantMessageId)
          if (existingMessage) {
            return prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: `Error: ${streamErrors[0]}`, isError: true }
                : msg
            )
          } else {
            // Create error message if it doesn't exist
            return [...prev, {
              role: 'assistant',
              content: `Error: ${streamErrors[0]}`,
              thinking_steps: [],
              timestamp: new Date().toISOString(),
              id: assistantMessageId,
              queryEventId: queryEventId,
              isError: true
            }]
          }
        })
      }

      trackResponse(
        responseContent,
        toolCalls,
        responseTime,
        responseContent.length > 0
      )

      streamingContentRef.current = ''
      streamingThinkingRef.current = []
      streamingErrorsRef.current = []
    }
  }

  const clearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      trackClearChat(messages.length)

      setMessages([])
      if (onClearChat) {
        onClearChat()
      }
    }
  }

  return (
    <div className="bg-white flex flex-col h-full">
      {/* Header - Only show if file is uploaded */}
      {uploadedFile && (
        <div className="border-b border-gray-100 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">
                Analyzing: {uploadedFile.filename}
              </p>
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
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-3xl font-medium text-gray-900 mb-2" style={{ letterSpacing: '-0.7px' }}>
                Analyze Excel files using AI-powered tools
              </h2>
              <p className="text-base text-gray-500" style={{ letterSpacing: '-0.7px' }}>
                {uploadedFile
                  ? 'Start asking questions about your data'
                  : 'Upload Excel files (.xlsx, .xls, .xlsm) up to 50MB'}
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

      {/* Input Area - AI Elements PromptInput */}
      <TooltipProvider delayDuration={300}>
        <div className="px-6 py-4">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.xlsm"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* File indicator */}
          {uploadedFile && (
            <div className="mb-3 flex items-center gap-2 p-2 bg-gray-50 border border-gray-200 rounded-md">
              <PaperclipIcon className="h-4 w-4 text-gray-600" />
              <span className="flex-1 text-sm text-gray-700 truncate">
                {uploadedFile.filename}
              </span>
              <button
                onClick={handleRemoveFile}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Remove file"
              >
                <XIcon className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Upload error indicator */}
          {uploadError && (
            <div className="mb-3 p-3 bg-red-50 border border-red-100 rounded-md">
              <p className="text-sm text-red-700">{uploadError}</p>
            </div>
          )}

          <PromptInput 
            onSubmit={async ({ text }) => {
              if (text.trim() && uploadedFile) {
                await handleSendMessage(text)
              }
            }}
            className="rounded-3xl"
          >
            <PromptInputBody>
              <PromptInputTextarea
                placeholder="Ask any deep analytical questions"
                disabled={!uploadedFile || sending}
                className="text-gray-600 placeholder:text-[#4B4B4B]"
              />
            </PromptInputBody>
            <PromptInputFooter>
              <PromptInputTools>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <PromptInputButton
                      onClick={handleAttachmentClick}
                      disabled={uploading}
                      aria-label="Upload Excel file"
                      className="text-gray-600 hover:text-gray-900"
                    >
                      <PaperclipIcon className="h-4 w-4" />
                    </PromptInputButton>
                  </TooltipTrigger>
                  <TooltipContent side="top" align="center">
                    <p>Excel files (.xlsx, .xls, .xlsm) up to 50MB</p>
                  </TooltipContent>
                </Tooltip>
              </PromptInputTools>
              <PromptInputSubmit 
                status={sending ? 'submitted' : undefined}
                disabled={!uploadedFile || sending}
                className="bg-[#7c2d3a] hover:bg-[#641f2d] text-white rounded-full"
              >
                {!sending && <ArrowUp className="h-4 w-4" />}
              </PromptInputSubmit>
            </PromptInputFooter>
          </PromptInput>
        </div>
      </TooltipProvider>
    </div>
  )
}

export default ChatInterface
