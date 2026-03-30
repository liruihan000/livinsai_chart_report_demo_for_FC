'use client'

import { useState } from 'react'

interface HeaderProps {
  onClearHistory: () => void
}

/** Top bar: logo + clear history button */
export function Header({ onClearHistory }: HeaderProps) {
  const [confirmClear, setConfirmClear] = useState(false)

  const handleClear = () => {
    if (confirmClear) {
      onClearHistory()
      setConfirmClear(false)
    } else {
      setConfirmClear(true)
      // Auto-reset after 3s
      setTimeout(() => setConfirmClear(false), 3000)
    }
  }

  return (
    <header className="flex items-center justify-between border-b px-6 py-3"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
      <h1 className="text-xl font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
        Livins Report
      </h1>
      <button
        onClick={handleClear}
        className="rounded-md px-3 py-1.5 text-sm transition-colors"
        style={{
          color: confirmClear ? 'var(--error)' : 'var(--text-secondary)',
          background: confirmClear ? 'rgba(199, 95, 95, 0.1)' : 'transparent',
        }}
      >
        {confirmClear ? '确认清除?' : '清除对话'}
      </button>
    </header>
  )
}
