'use client'

import { useState } from 'react'

interface HeaderProps {
  onClearHistory: () => void
  hasMessages: boolean
  hasFiles: boolean
  isPanelOpen: boolean
  onTogglePanel: () => void
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

export function Header({
  onClearHistory,
  hasMessages,
  hasFiles,
  isPanelOpen,
  onTogglePanel,
}: HeaderProps) {
  const [confirmClear, setConfirmClear] = useState(false)

  const handleClear = () => {
    if (confirmClear) {
      onClearHistory()
      setConfirmClear(false)
    } else {
      setConfirmClear(true)
      setTimeout(() => setConfirmClear(false), 3000)
    }
  }

  return (
    <header
      className="flex items-center justify-between px-8 py-4"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <span
        className="text-sm font-medium tracking-wide"
        style={{ color: 'var(--text-secondary)', letterSpacing: '0.04em' }}
      >
        Livins Report
      </span>
      <div className="flex items-center gap-4">
        {hasFiles && (
          <button
            onClick={onTogglePanel}
            className="flex items-center gap-1.5 text-xs transition-colors"
            style={{
              color: isPanelOpen ? 'var(--text-primary)' : 'var(--text-muted)',
              padding: '4px 10px',
              border: '1px solid var(--border)',
              borderRadius: '14px',
              background: isPanelOpen ? 'var(--accent-subtle)' : 'transparent',
            }}
          >
            <FileIcon />
            文件
          </button>
        )}
        {hasMessages && (
          <button
            onClick={handleClear}
            className="text-xs transition-colors"
            style={{
              color: confirmClear ? 'var(--error)' : 'var(--text-muted)',
              padding: '4px 0',
            }}
          >
            {confirmClear ? '确认清除' : '清除对话'}
          </button>
        )}
      </div>
    </header>
  )
}
