'use client'

import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import type { ChatMessage } from '@/lib/types'

interface ChatContainerProps {
  messages: ChatMessage[]
  isLoading: boolean
  onSendMessage: (content: string) => Promise<void>
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

/** Orchestrator: combines MessageList + InputBar */
export function ChatContainer({
  messages,
  isLoading,
  onSendMessage,
  onViewReport,
}: ChatContainerProps) {
  return (
    <div className="flex flex-1 flex-col" style={{ borderRight: '1px solid var(--border)' }}>
      <MessageList messages={messages} isLoading={isLoading} onViewReport={onViewReport} />
      <InputBar onSend={onSendMessage} disabled={isLoading} />
    </div>
  )
}
