import React from 'react'
import { Navbar } from '../components/Navbar'
import { Sidebar } from '../components/Sidebar'
import { MessagesList } from '../components/MessagesList'
import { ChatInput } from '../components/ChatInput'
import { useChatStore } from '../store/chat'
import { useUIStore } from '../store/ui'
import { cn } from '../utils'

const ChatPage: React.FC = () => {
  const { sidebarOpen } = useUIStore()
  const { loadThreads, messages, currentThread, isTyping } = useChatStore()

  React.useEffect(() => {
    loadThreads().catch(error => {
      console.error('ChatPage: Failed to load threads:', error);
    });
  }, [loadThreads])

  return (
    <div className="h-full flex flex-col">
      <Navbar />
      <Sidebar />
      
      {/* Main Content */}
      <main className={cn(
        'pt-16 h-full transition-all duration-200',
        sidebarOpen ? 'lg:ml-64' : ''
      )}>
        <div className="h-full flex flex-col max-w-4xl mx-auto bg-white dark:bg-gray-800 shadow-lg">
          {/* Chat Header */}
          <div className="border-b border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {currentThread?.title || 'New Chat'}
                </h2>
                {currentThread && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {messages.length} messages
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Messages */}
          <MessagesList messages={messages} isTyping={isTyping} />

          {/* Input */}
          <ChatInput />
        </div>
      </main>
    </div>
  )
}

export default ChatPage