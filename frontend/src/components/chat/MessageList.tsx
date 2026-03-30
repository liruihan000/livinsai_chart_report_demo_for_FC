'use client'

import { useRef, useEffect } from 'react'
import { MessageBubble, StreamingMessage } from './MessageBubble'
import type { ChatMessage, ToolStep } from '@/lib/types'

interface MessageListProps {
  messages: ChatMessage[]
  isLoading: boolean
  activeToolSteps: ToolStep[]
  thinkingText: string
  streamingContent: string
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

export function MessageList({
  messages,
  isLoading,
  activeToolSteps,
  thinkingText,
  streamingContent,
  onViewReport,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, activeToolSteps, streamingContent])

  return (
    <div className="flex-1 overflow-y-auto pt-10 pb-4" style={{ scrollBehavior: 'smooth' }}>
      <div className="mx-auto w-full px-6" style={{ maxWidth: '768px' }}>
      {messages.length === 0 && !isLoading && (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            输入问题，开始分析房源数据
          </p>
        </div>
      )}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} onViewReport={onViewReport} />
      ))}
      {isLoading && (
        <StreamingMessage toolSteps={activeToolSteps} thinkingText={thinkingText} content={streamingContent} />
      )}
      <div ref={bottomRef} />
      </div>
    </div>
  )
}
