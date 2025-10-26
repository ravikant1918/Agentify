import React from 'react'
import TextareaAutosize from 'react-textarea-autosize'
import { PaperAirplaneIcon } from '@heroicons/react/24/solid'
import { Button } from './Button'
import { useChatStore } from '../store/chat'

export const ChatInput: React.FC = () => {
  const [message, setMessage] = React.useState('')
  const { sendMessage, isTyping } = useChatStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isTyping) return

    const messageToSend = message.trim()
    setMessage('')
    await sendMessage(messageToSend)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Listen for quick messages from welcome screen
  React.useEffect(() => {
    const handleQuickMessage = (e: CustomEvent) => {
      setMessage(e.detail)
    }

    window.addEventListener('quickMessage', handleQuickMessage as EventListener)
    return () => window.removeEventListener('quickMessage', handleQuickMessage as EventListener)
  }, [])

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 p-4">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="flex-1">
          <TextareaAutosize
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
            minRows={1}
            maxRows={6}
            disabled={isTyping}
          />
        </div>
        
        <Button
          type="submit"
          disabled={!message.trim() || isTyping}
          isLoading={isTyping}
          className="self-end"
        >
          <PaperAirplaneIcon className="h-5 w-5" />
        </Button>
      </form>
      
      {isTyping && (
        <div className="mt-2 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-600 border-t-transparent" />
          <span>AI is thinking...</span>
        </div>
      )}
    </div>
  )
}