import React from 'react'
import { Message } from '../utils/api'
import { formatTime, cn } from '../utils'

interface MessageBubbleProps {
  message: Message
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="max-w-xs px-3 py-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-full">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'group relative max-w-xs lg:max-w-md px-4 py-3 rounded-2xl',
          isUser
            ? 'bg-primary-600 text-white rounded-br-md'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-bl-md'
        )}
      >
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <div
          className={cn(
            'mt-1 text-xs opacity-70',
            isUser ? 'text-primary-100' : 'text-gray-500 dark:text-gray-400'
          )}
        >
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  )
}

interface MessagesListProps {
  messages: Message[]
  isTyping: boolean
}

export const MessagesList: React.FC<MessagesListProps> = ({ messages, isTyping }) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 ? (
        <WelcomeMessage />
      ) : (
        messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))
      )}
      
      {isTyping && <TypingIndicator />}
      <div ref={messagesEndRef} />
    </div>
  )
}

const WelcomeMessage: React.FC = () => {
  return (
    <div className="text-center py-12">
      <div className="mb-4">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
        Welcome to Agentify
      </h3>
      <p className="text-gray-500 dark:text-gray-400 mb-6">
        Start a conversation with your AI assistant
      </p>

      {/* Quick Actions */}
      <div className="flex flex-wrap justify-center gap-2">
        {['What tools are available?', 'Help me get started', 'Show me examples'].map((text) => (
          <button
            key={text}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            onClick={() => {
              // This will be handled by the parent component
              const event = new CustomEvent('quickMessage', { detail: text })
              window.dispatchEvent(event)
            }}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}

const TypingIndicator: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}