'use client'

import { useRef, useEffect } from 'react'
import { MessageBubble } from './MessageBubble'
import { StreamingDots } from './StreamingDots'
import type { ChatMessage } from '@/lib/types'

interface MessageListProps {
  messages: ChatMessage[]
  isLoading: boolean
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

/** Scrollable message list with auto-scroll to bottom */
export function MessageList({ messages, isLoading, onViewReport }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
      {messages.length === 0 && (
        <div className="flex h-full items-center justify-center">
          <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-display)' }}
            className="text-lg">
            Ask me about housing data...
          </p>
        </div>
      )}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} onViewReport={onViewReport} />
      ))}
      {isLoading && <StreamingDots />}
      <div ref={bottomRef} />
    </div>
  )
}
