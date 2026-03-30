'use client'

import { useState, useCallback, useRef, type KeyboardEvent, type ChangeEvent } from 'react'

interface InputBarProps {
  onSend: (content: string) => Promise<void>
  disabled: boolean
}

/** Auto-resizing textarea + send button. Enter to send, Shift+Enter for newline. */
export function InputBar({ onSend, disabled }: InputBarProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || disabled) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    await onSend(trimmed)
  }, [input, disabled, onSend])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize up to 4 lines
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 96) + 'px'
  }

  return (
    <div className="border-t px-6 py-4" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
      <div className="flex items-end gap-3 rounded-xl px-4 py-2"
        style={{ background: 'var(--bg-tertiary)' }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm outline-none"
          style={{ color: 'var(--text-primary)', maxHeight: '96px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="rounded-lg px-3 py-1.5 text-sm font-medium transition-all hover:scale-105 active:scale-95 disabled:opacity-40"
          style={{ background: 'var(--accent)', color: 'var(--bg-primary)' }}
        >
          发送
        </button>
      </div>
    </div>
  )
}
