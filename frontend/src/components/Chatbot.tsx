import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User } from 'lucide-react'
import { api } from '../services/api'

// Enhanced markdown parser for formatting LLM responses with better structure
const formatMessage = (text: string): JSX.Element[] => {
  if (!text) return [<p key="empty" className="text-base text-gray-600">No response</p>]
  
  const lines = text.split('\n')
  const formatted: JSX.Element[] = []
  let currentList: JSX.Element[] = []
  let inList = false
  let listKey = 0
  let paragraphBuffer: string[] = []
  let sectionKey = 0
  
  const closeList = () => {
    if (inList && currentList.length > 0) {
      formatted.push(
        <ul key={`list-${listKey++}`} className="list-disc list-inside space-y-2 mb-6 ml-5 text-base leading-7 text-gray-800">
          {currentList}
        </ul>
      )
      currentList = []
      inList = false
    }
  }
  
  const flushParagraph = () => {
    if (paragraphBuffer.length > 0) {
      const paragraphText = paragraphBuffer.join(' ').trim()
      if (paragraphText) {
        formatted.push(
          <p key={`p-${formatted.length}`} className="text-base mb-5 leading-7 text-gray-800">
            {processInlineFormatting(paragraphText)}
          </p>
        )
      }
      paragraphBuffer = []
    }
  }
  
  const processInlineFormatting = (text: string): (string | JSX.Element)[] => {
    const parts: (string | JSX.Element)[] = []
    let lastIndex = 0
    const boldRegex = /\*\*(.*?)\*\*/g
    let match
    let keyIndex = 0
    
    while ((match = boldRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const beforeText = text.substring(lastIndex, match.index).replace(/\*/g, '')
        if (beforeText) {
          parts.push(beforeText)
        }
      }
      parts.push(<strong key={`bold-${keyIndex++}`} className="font-semibold text-gray-900">{match[1]}</strong>)
      lastIndex = match.index + match[0].length
    }
    
    if (lastIndex < text.length) {
      const afterText = text.substring(lastIndex).replace(/\*/g, '')
      if (afterText) {
        parts.push(afterText)
      }
    }
    
    if (parts.length === 0) {
      return [text.replace(/\*/g, '')]
    }
    
    return parts.length > 0 ? parts : [text.replace(/\*/g, '')]
  }
  
  const isBiomarkerLine = (line: string): boolean => {
    return /^[\*\-\s]*[A-Z][^:]+\([^)]+\):/.test(line.trim()) || 
           /^[\*\-\s]*[A-Z][^:]+\([^)]+\)\s+\(/.test(line.trim())
  }
  
  const isSectionHeader = (line: string): boolean => {
    const trimmed = line.trim()
    return (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.split('**').length === 3) ||
           (!!trimmed.match(/^[A-Z][^:]+:$/) && trimmed.length < 100)
  }
  
  lines.forEach((line, index) => {
    const trimmed = line.trim()
    
    // Handle headers (###)
    if (trimmed.startsWith('### ')) {
      flushParagraph()
      closeList()
      formatted.push(
        <div key={`section-${sectionKey++}`} className="mt-8 mb-6">
          <h3 className="font-bold text-lg text-gray-900 mb-4 pb-3 border-b-2 border-gray-300">
            {trimmed.replace('### ', '')}
          </h3>
        </div>
      )
      return
    }
    
    // Handle horizontal rules
    if (trimmed === '---' || trimmed === '***') {
      flushParagraph()
      closeList()
      formatted.push(<hr key={`hr-${index}`} className="my-6 border-gray-300" />)
      return
    }
    
    // Handle section headers
    if (isSectionHeader(trimmed)) {
      flushParagraph()
      closeList()
      const headerText = trimmed.replace(/\*/g, '').replace(/:$/, '')
      formatted.push(
        <div key={`section-header-${index}`} className="mt-8 mb-5">
          <h4 className="font-bold text-base text-gray-900 uppercase tracking-wide mb-4">
            {headerText}
          </h4>
        </div>
      )
      return
    }
    
    // Handle biomarker result lines
    if (isBiomarkerLine(trimmed)) {
      flushParagraph()
      closeList()
      
      const match = trimmed.match(/^[\*\-\s]*(.+?)\s*\(([^)]+)\):\s*(.+)$/) ||
                    trimmed.match(/^[\*\-\s]*(.+?)\s*\(([^)]+)\)\s+\((.+)\):\s*(.+)$/)
      
      if (match) {
        const name = match[1].trim().replace(/\*/g, '')
        const value = match[2].trim()
        const description = (match[3] || match[4] || '').trim()
        
        formatted.push(
          <div key={`biomarker-${index}`} className="mb-5 pl-5 border-l-4 border-blue-500 bg-blue-50/40 py-3 pr-4 rounded-r-lg">
            <div className="flex items-start gap-3 mb-2">
              <span className="font-semibold text-base text-gray-900">{name}:</span>
              <span className="text-base text-gray-700 font-mono font-medium">{value}</span>
            </div>
            {description && (
              <p className="text-base text-gray-700 mt-2 leading-7">
                {processInlineFormatting(description)}
              </p>
            )}
          </div>
        )
      } else {
        formatted.push(
          <div key={`biomarker-fallback-${index}`} className="mb-4 pl-5 border-l-4 border-blue-500 bg-blue-50/40 py-3 pr-4 rounded-r-lg">
            <p className="text-base text-gray-800 leading-7">
              {processInlineFormatting(trimmed.replace(/^[\*\-\s]+/, '').replace(/\*/g, ''))}
            </p>
          </div>
        )
      }
      return
    }
    
    // Handle list items
    if (trimmed.match(/^[\*\-\s]+\*\*/) || trimmed.match(/^[\*\-\s]+[A-Z]/) || 
        (trimmed.startsWith('*   ') || trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('1. ') || trimmed.startsWith('•'))) {
      flushParagraph()
      inList = true
      const itemText = trimmed.replace(/^[\*\-\d\.\s•]+/, '').trim().replace(/\*/g, '')
      if (itemText) {
        const processedItem = processInlineFormatting(itemText)
        currentList.push(
          <li key={`item-${currentList.length}`} className="text-base leading-7 mb-2.5 text-gray-800">
            {processedItem}
          </li>
        )
      }
      return
    }
    
    // Handle "What this means:" or similar bold phrases
    if (trimmed.match(/^\*\*[^*]+\*\*:/)) {
      flushParagraph()
      closeList()
      const parts = trimmed.split(/(\*\*.*?\*\*:)/)
      formatted.push(
        <div key={`bold-start-${index}`} className="mb-4 mt-5">
          <p className="text-base leading-7 text-gray-800">
            {parts.map((part, i) => {
              if (part.match(/^\*\*.*?\*\*:$/)) {
                return <strong key={i} className="font-bold text-gray-900 text-lg">{part.replace(/\*/g, '')}</strong>
              }
              return <span key={i}>{processInlineFormatting(part)}</span>
            })}
          </p>
        </div>
      )
      return
    }
    
    // Handle summary lines
    if (trimmed.match(/^(In summary|Overall|To summarize|Summary):/i)) {
      flushParagraph()
      closeList()
      formatted.push(
        <div key={`summary-${index}`} className="mt-6 mb-5 p-4 bg-gray-100 rounded-lg border-l-4 border-gray-500">
          <p className="text-base font-medium leading-7 text-gray-900">
            {processInlineFormatting(trimmed)}
          </p>
        </div>
      )
      return
    }
    
    // Handle regular paragraphs
    if (trimmed) {
      if (trimmed.length > 0 && !trimmed.match(/^[A-Z]/) && paragraphBuffer.length > 0) {
        paragraphBuffer.push(trimmed)
      } else {
        flushParagraph()
        paragraphBuffer.push(trimmed)
      }
    } else {
      flushParagraph()
      if (formatted.length > 0 && formatted[formatted.length - 1].type !== 'div') {
        formatted.push(<div key={`spacer-${index}`} className="h-4" />)
      }
    }
  })
  
  flushParagraph()
  closeList()
  
  return formatted.length > 0 ? formatted : [<p key="default" className="text-base leading-7 text-gray-800">{text}</p>]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatbotProps {
  sessionId: string
  biomarkers?: any[]
}

export default function Chatbot({ sessionId }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I can help answer questions about your lab results. What would you like to know?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }

    try {
      const response = await api.chat(sessionId, input)
      const assistantMessage: Message = { role: 'assistant', content: response.message }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error?.response?.data?.detail || error?.message || 'Unknown error'}`
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
  }

  return (
    <div className="flex flex-col h-[650px] bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-5 py-6 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center mt-1">
                  <Bot className="w-5 h-5 text-gray-600" />
                </div>
              )}
              
              <div
                className={`${message.role === 'user' ? 'order-2 max-w-[85%]' : 'order-1 flex-1'}`}
              >
                <div
                  className={`rounded-2xl px-5 py-4 ${
                    message.role === 'user'
                      ? 'bg-[#19c37d] text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="text-base leading-7 whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="text-base leading-7 max-w-none">
                      {formatMessage(message.content)}
                    </div>
                  )}
                </div>
              </div>

              {message.role === 'user' && (
                <div className="flex-shrink-0 w-9 h-9 rounded-full bg-[#19c37d] flex items-center justify-center mt-1 order-3">
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
            </div>
          ))}
          
          {loading && (
            <div className="flex gap-4 justify-start">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center mt-1">
                <Bot className="w-5 h-5 text-gray-600" />
              </div>
              <div className="flex-1 max-w-[85%]">
                <div className="bg-gray-100 rounded-2xl px-5 py-4">
                  <div className="flex space-x-2">
                    <div className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2.5 h-2.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area - Fixed at Bottom */}
      <div className="border-t border-gray-200 bg-white px-5 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3 bg-white border border-gray-300 rounded-2xl px-5 py-3 shadow-sm hover:border-gray-400 focus-within:border-[#19c37d] focus-within:ring-2 focus-within:ring-[#19c37d]/20 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Message..."
              rows={1}
              className="flex-1 resize-none border-0 focus:outline-none focus:ring-0 text-base py-1 max-h-[200px] overflow-y-auto bg-transparent text-gray-900 placeholder-gray-400"
              style={{ minHeight: '28px', lineHeight: '1.5' }}
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                input.trim() && !loading
                  ? 'bg-[#19c37d] hover:bg-[#16b372] text-white shadow-sm hover:shadow'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">
            MediStream can make mistakes. Check important info.
          </p>
        </div>
      </div>
    </div>
  )
}
