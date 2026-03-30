'use client'

import type { ChatMessage } from '@/lib/types'

interface MessageBubbleProps {
  message: ChatMessage
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

/**
 * Single message bubble.
 * - User: right-aligned, accent background
 * - Assistant: left-aligned, secondary background, supports Markdown
 */
export function MessageBubble({ message, onViewReport }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  // TODO: Add react-markdown rendering for assistant messages
  // TODO: Parse report links from content and wire onViewReport

  return (
    <div className={`mb-3 flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className="max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
        style={{
          background: isUser ? 'var(--accent-subtle)' : 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          borderBottomRightRadius: isUser ? '4px' : undefined,
          borderBottomLeftRadius: !isUser ? '4px' : undefined,
        }}
      >
        {message.content}
      </div>
    </div>
  )
}
