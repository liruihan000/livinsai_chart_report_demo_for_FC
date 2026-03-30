'use client'

import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import type { ChatMessage, ToolStep } from '@/lib/types'

interface ChatContainerProps {
  messages: ChatMessage[]
  isLoading: boolean
  activeToolSteps: ToolStep[]
  thinkingText: string
  streamingContent: string
  onSendMessage: (content: string) => Promise<void>
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

export function ChatContainer({
  messages,
  isLoading,
  activeToolSteps,
  thinkingText,
  streamingContent,
  onSendMessage,
  onViewReport,
}: ChatContainerProps) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <MessageList
        messages={messages}
        isLoading={isLoading}
        activeToolSteps={activeToolSteps}
        thinkingText={thinkingText}
        streamingContent={streamingContent}
        onViewReport={onViewReport}
      />
      <InputBar onSend={onSendMessage} disabled={isLoading} />
    </div>
  )
}
