'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useLocalStorage } from './useLocalStorage'
import { chatStream } from '@/lib/api'
import { STORAGE_KEYS } from '@/lib/storage'
import type { ChatMessage, FileRef, ToolStep } from '@/lib/types'

export interface UseChatReturn {
  messages: ChatMessage[]
  isLoading: boolean
  /** Tool steps for the in-flight assistant message (while streaming) */
  activeToolSteps: ToolStep[]
  /** Intermediate thinking text (gray italic, shown during processing) */
  thinkingText: string
  /** Final response content being streamed */
  streamingContent: string
  sendMessage: (content: string) => Promise<void>
  clearHistory: () => void
  files: FileRef[] | null
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useLocalStorage<ChatMessage[]>(STORAGE_KEYS.MESSAGES, [])
  const [sessionId, setSessionId] = useLocalStorage<string>(STORAGE_KEYS.SESSION_ID, '')
  const [isLoading, setIsLoading] = useState(false)
  const [files, setFiles] = useState<FileRef[] | null>(null)
  const [activeToolSteps, setActiveToolSteps] = useState<ToolStep[]>([])
  const [thinkingText, setThinkingText] = useState('')
  const [streamingContent, setStreamingContent] = useState('')

  // Refs to avoid stale closures in stream callbacks
  const toolStepsRef = useRef<ToolStep[]>([])
  const contentRef = useRef('')
  const pendingThinkingRef = useRef('')

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
      setActiveToolSteps([])
      setThinkingText('')
      setStreamingContent('')
      toolStepsRef.current = []
      contentRef.current = ''
      pendingThinkingRef.current = ''

      try {
        await chatStream(updatedMessages, sessionId, {
          onSession: (sid) => {
            if (!sessionId) setSessionId(sid)
          },
          onThinking: (text) => {
            // Store pending thinking — will be attached to next tool_start
            pendingThinkingRef.current = text
            setThinkingText(text)
          },
          onToolStart: (name, label, input) => {
            // Attach pending thinking to this step
            const step: ToolStep = {
              name, label, input, status: 'running',
              thinking: pendingThinkingRef.current || undefined,
            }
            pendingThinkingRef.current = ''
            setThinkingText('')
            toolStepsRef.current = [...toolStepsRef.current, step]
            setActiveToolSteps([...toolStepsRef.current])
          },
          onToolEnd: (name) => {
            toolStepsRef.current = toolStepsRef.current.map((s) =>
              s.name === name && s.status === 'running' ? { ...s, status: 'done' } : s,
            )
            setActiveToolSteps([...toolStepsRef.current])
          },
          onToken: (token) => {
            setThinkingText('')
            contentRef.current += token
            setStreamingContent(contentRef.current)
          },
          onDone: (streamFiles) => {
            const steps = toolStepsRef.current
            const assistantMessage: ChatMessage = {
              role: 'assistant',
              content: contentRef.current,
              toolSteps: steps.length > 0 ? steps : undefined,
            }
            setMessages([...updatedMessages, assistantMessage])
            setActiveToolSteps([])
            setThinkingText('')
            setStreamingContent('')
            if (streamFiles.length > 0) {
              setFiles(streamFiles)
            }
          },
          onError: (detail) => {
            console.error('Stream error:', detail)
            const errorMessage: ChatMessage = {
              role: 'assistant',
              content: '抱歉，请求失败，请稍后重试。',
            }
            setMessages([...updatedMessages, errorMessage])
          },
        })
      } catch (error) {
        console.error('Chat stream failed:', error)
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: '抱歉，请求失败，请稍后重试。',
        }
        setMessages([...updatedMessages, errorMessage])
      } finally {
        setIsLoading(false)
      }
    },
    [messages, sessionId, setMessages, setSessionId],
  )

  const clearHistory = useCallback(() => {
    setMessages([])
    setFiles(null)
    setActiveToolSteps([])
    setThinkingText('')
    setStreamingContent('')
    setSessionId(crypto.randomUUID())
  }, [setMessages, setSessionId])

  return {
    messages, isLoading, activeToolSteps, thinkingText,
    streamingContent, sendMessage, clearHistory, files,
  }
}
