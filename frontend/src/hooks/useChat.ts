'use client'

import { useState, useCallback, useEffect } from 'react'
import { useLocalStorage } from './useLocalStorage'
import { chatRequest } from '@/lib/api'
import { STORAGE_KEYS } from '@/lib/storage'
import type { ChatMessage, FileRef } from '@/lib/types'

export interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  sendMessage: (content: string) => Promise<void>
  clearHistory: () => void
  files: FileRef[] | null
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useLocalStorage<ChatMessage[]>(STORAGE_KEYS.MESSAGES, [])
  const [sessionId, setSessionId] = useLocalStorage<string>(STORAGE_KEYS.SESSION_ID, '')
  const [isLoading, setIsLoading] = useState(false)
  const [files, setFiles] = useState<FileRef[] | null>(null)

  // Generate session ID on first mount if not present
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID())
    }
  }, [sessionId, setSessionId])

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = { role: 'user', content }
      const updatedMessages = [...messages, userMessage]
      setMessages(updatedMessages)
      setIsLoading(true)

      try {
        const response = await chatRequest(updatedMessages, sessionId)
        const assistantMessage: ChatMessage = { role: 'assistant', content: response.reply }
        setMessages([...updatedMessages, assistantMessage])

        if (response.files?.length) {
          setFiles(response.files)
        }
      } catch (error) {
        console.error('Chat request failed:', error)
        // Mark failed message so UI can show retry
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: '抱歉，请求失败，请稍后重试。',
        }
        setMessages([...updatedMessages, errorMessage])
      } finally {
        setIsLoading(false)
      }
    },
    [messages, sessionId, setMessages],
  )

  const clearHistory = useCallback(() => {
    setMessages([])
    setFiles(null)
    setSessionId(crypto.randomUUID())
  }, [setMessages, setSessionId])

  return { messages, isLoading, sendMessage, clearHistory, files }
}
