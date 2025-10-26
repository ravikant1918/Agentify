import React from 'react'
import { TrashIcon, ChatBubbleLeftIcon } from '@heroicons/react/24/outline'
import { useChatStore } from '../store/chat'
import { useUIStore } from '../store/ui'
import { Thread } from '../utils/api'
import { formatDate, cn } from '../utils'

export const Sidebar: React.FC = () => {
  const { sidebarOpen, setSidebarOpen } = useUIStore()
  const { threads, currentThread, selectThread, deleteThread, isLoading } = useChatStore()

  const handleThreadSelect = async (threadId: string) => {
    await selectThread(threadId)
    setSidebarOpen(false) // Close sidebar on mobile after selection
  }

  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this thread?')) {
      await deleteThread(threadId)
    }
  }

  return (
    <>
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-gray-600 bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 glass border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="h-16"></div> {/* Navbar spacer */}
        
        <div className="p-4 h-[calc(100vh-4rem)] overflow-y-auto">
          <div className="space-y-2">
            {isLoading ? (
              <div className="animate-pulse space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
                ))}
              </div>
            ) : threads && threads.length === 0 ? (
              <div className="text-center py-8">
                <ChatBubbleLeftIcon className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  No conversations yet
                </p>
              </div>
            ) : threads && Array.isArray(threads) ? (
              threads.map((thread) => (
                <ThreadItem
                  key={thread.id}
                  thread={thread}
                  isActive={currentThread?.id === thread.id}
                  onSelect={() => handleThreadSelect(thread.id)}
                  onDelete={(e) => handleDeleteThread(e, thread.id)}
                />
              ))
            ) : null}
          </div>
        </div>
      </aside>
    </>
  )
}

interface ThreadItemProps {
  thread: Thread
  isActive: boolean
  onSelect: () => void
  onDelete: (e: React.MouseEvent) => void
}

const ThreadItem: React.FC<ThreadItemProps> = ({ thread, isActive, onSelect, onDelete }) => {
  return (
    <div
      onClick={onSelect}
      className={cn(
        'group relative p-3 rounded-lg cursor-pointer transition-colors duration-200',
        isActive
          ? 'bg-primary-100 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className={cn(
            'text-sm font-medium truncate',
            isActive
              ? 'text-primary-900 dark:text-primary-100'
              : 'text-gray-900 dark:text-gray-100'
          )}>
            {thread.title}
          </h3>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
            {thread.last_message}
          </p>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {formatDate(thread.updated_at)}
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {thread.message_count} messages
            </span>
          </div>
        </div>
        
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 ml-2 p-1 rounded text-gray-400 hover:text-red-500 transition-all duration-200"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}