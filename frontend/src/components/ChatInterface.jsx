import { useState, useRef, useEffect, useCallback } from 'react'
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
  PromptInputButton,
  PromptInputProvider,
  usePromptInputController
} from '@/components/ai-elements/prompt-input'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { PaperclipIcon, XIcon, ArrowUp, Code, X } from 'lucide-react'
import { useSpreadsheet } from '../contexts/SpreadsheetContext'

function ChatInterface({ uploadedFile, apiBaseUrl, onClearChat, onFileUpload, onSheetUpdated }) {
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
  const { sheets, pendingCellReference, clearPendingCellReference, setAiCursor } = useSpreadsheet(); // Get sheets and cell reference from context
  
  // Handler for AI cursor events
  const onAiCursor = useCallback((cursorData) => {
    setAiCursor(cursorData);
    // Clear cursor after a delay
    if (cursorData) {
      setTimeout(() => setAiCursor(null), 3000);
    }
  }, [setAiCursor]);

    // Format suggestions for mentions
    const suggestions = [
        // Add sheets
        ...(sheets || []).map(sheet => ({
            id: sheet.name,
            label: sheet.name,
            value: sheet.name,
            icon: <span className="material-symbols-rounded text-base">rubric</span>
        })),
    // Add special items if needed
    { id: 'code', label: 'Code', value: 'code', icon: <Code className="w-4 h-4" /> }
  ];

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
    // Clear messages when file is removed
    if (!uploadedFile) {
      setMessages([])
      welcomeShownForFile.current = null
    } else {
      welcomeShownForFile.current = uploadedFile.file_path
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

    // Include cell reference in message if present
    let finalMessage = userInputMessage
    let displayMessage = userInputMessage
    if (pendingCellReference) {
      const cellRef = `[Referencing ${pendingCellReference.sheet}!${pendingCellReference.range}]`
      finalMessage = `${cellRef}\n\n${userInputMessage}`
      displayMessage = userInputMessage
      clearPendingCellReference()
    }

    const userMessageId = Date.now()
    const userMessage = {
      role: 'user',
      content: displayMessage,
      cellReference: pendingCellReference ? `${pendingCellReference.sheet}!${pendingCellReference.range}` : null,
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
          message: finalMessage,
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
              } else if (parsed.type === 'sheet_updated') {
                onSheetUpdated?.(parsed)
              } else if (parsed.type === 'ai_cursor') {
                // Update AI cursor position in spreadsheet
                onAiCursor?.(parsed.location ? { ...parsed.location, tool_name: parsed.tool_name } : null)
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
          <div className="h-full flex flex-col items-center justify-center">
            <div className="text-center mb-8">
              <h2 className="text-lg font-medium text-gray-900 mb-2">
                Perform analysis on your structured files
              </h2>
              <p className="text-sm text-gray-500">
                {uploadedFile
                  ? `Analyzing: ${uploadedFile.filename}`
                  : 'Upload Excel files (.xlsx, .xls, .xlsm) up to 50MB'}
              </p>
            </div>
            
            {/* Suggestion Cards */}
            <div className="w-full max-w-2xl space-y-3">
              <SuggestionCard
                title="Summarize my data"
                description="Get a comprehensive overview of all sheets and columns"
                icon="summarize"
                onClick={() => {
                  if (uploadedFile) {
                    handleSendMessage("Give me a comprehensive summary of all the data in this file, including key statistics and patterns.")
                  }
                }}
                disabled={!uploadedFile}
              />
              <SuggestionCard
                title="Find trends & patterns"
                description="Discover correlations and trends across your data"
                icon="trending_up"
                onClick={() => {
                  if (uploadedFile) {
                    handleSendMessage("Analyze this data and identify any significant trends, patterns, or correlations.")
                  }
                }}
                disabled={!uploadedFile}
              />
              <SuggestionCard
                title="Create a visualization"
                description="Generate charts and graphs from your data"
                icon="insert_chart"
                onClick={() => {
                  if (uploadedFile) {
                    handleSendMessage("Create appropriate visualizations (charts/graphs) to represent the key insights in this data.")
                  }
                }}
                disabled={!uploadedFile}
              />
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
            <div className="mb-3 flex items-center gap-2 p-2 bg-gray-50 border border-gray-200 rounded-2xl">
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

          {/* Cell reference indicator */}
          {pendingCellReference && (
            <div className="mb-3 flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-2xl">
              <span className="material-symbols-rounded text-blue-600 text-base">grid_on</span>
              <span className="flex-1 text-sm text-blue-700">
                Referencing: <span className="font-mono font-medium">{pendingCellReference.sheet}!{pendingCellReference.range}</span>
              </span>
              <button
                onClick={clearPendingCellReference}
                className="text-blue-400 hover:text-blue-600 transition-colors"
                aria-label="Remove cell reference"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Upload error indicator */}
          {uploadError && (
            <div className="mb-3 p-3 bg-red-50 border border-red-100 rounded-md">
              <p className="text-sm text-red-700">{uploadError}</p>
            </div>
          )}

          <PromptInputProvider>
            <div className="[&_[data-slot=input-group]]:rounded-2xl">
              <PromptInput
                onSubmit={async ({ text }) => {
                  if (text.trim() && uploadedFile) {
                    await handleSendMessage(text)
                  }
                }}
              >
              <PromptInputBody>
                <PromptInputTextarea
                  placeholder="Ask any deep analytical questions (type @ to mention sheets)"
                  disabled={!uploadedFile || sending}
                  className="text-gray-600 placeholder:text-[#4B4B4B]"
                  suggestions={suggestions}
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
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <MentionButton />
                    </TooltipTrigger>
                    <TooltipContent side="top" align="center">
                      <p>Mention a sheet (@)</p>
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
          </PromptInputProvider>
        </div>
      </TooltipProvider>
    </div>
  )
}

function MentionButton() {
  const controller = usePromptInputController();

  const handleClick = () => {
    const current = controller.textInput.value;
    controller.textInput.setInput(current + (current.endsWith(' ') || current.length === 0 ? '@' : ' @'));
    // We would ideally focus the input too, but the controller doesn't expose focus directly yet.
    // However, PromptInputTextarea listens to changes.
    // To focus, we might need a ref to the textarea, but let's start with just appending text.
  };

  return (
    <PromptInputButton
      onClick={handleClick}
      aria-label="Mention sheet"
      className="text-gray-600 hover:text-gray-900"
    >
      <span className="text-lg font-medium leading-none">@</span>
    </PromptInputButton>
  )
}

function SuggestionCard({ title, description, icon, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full text-left p-4 rounded-xl border border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm transition-all group ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-medium text-gray-900 mb-1 group-hover:text-gray-700">
            {title}
          </h3>
          <p className="text-sm text-gray-500">
            {description}
          </p>
        </div>
        <div className="shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center group-hover:bg-gray-200 transition-colors">
          <span className="material-symbols-rounded text-gray-600 text-xl">{icon}</span>
        </div>
      </div>
    </button>
  )
}

export default ChatInterface
