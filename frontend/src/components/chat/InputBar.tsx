'use client'

import { useState, useCallback, useRef, type KeyboardEvent, type ChangeEvent } from 'react'

interface InputBarProps {
  onSend: (content: string) => Promise<void>
  disabled: boolean
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  )
}

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
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 110) + 'px'
  }

  return (
    <div className="pb-6 pt-2">
      <div
        className="mx-auto w-full px-6"
        style={{ maxWidth: '768px' }}
      >
      <div
        className="flex items-end gap-2 px-5 py-2.5"
        style={{
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-input)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm outline-none"
          style={{
            color: 'var(--text-primary)',
            minHeight: '26px',
            maxHeight: '110px',
            lineHeight: '1.5',
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="flex shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-30"
          style={{
            width: '36px',
            height: '36px',
            background: disabled || !input.trim() ? 'var(--text-muted)' : '#9b9690',
          }}
        >
          <SendIcon />
        </button>
      </div>
      </div>
    </div>
  )
}
