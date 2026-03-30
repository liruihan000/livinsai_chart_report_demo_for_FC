'use client'

interface PdfToolbarProps {
  onClose: () => void
  onDownload: () => void
}

/** PDF panel toolbar: download + close buttons */
export function PdfToolbar({ onClose, onDownload }: PdfToolbarProps) {
  return (
    <div
      className="flex items-center justify-between border-b px-4 py-2"
      style={{ borderColor: 'var(--border)' }}
    >
      <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
        Report Preview
      </span>
      <div className="flex gap-2">
        <button
          onClick={onDownload}
          className="rounded-md px-2.5 py-1 text-xs transition-colors hover:opacity-80"
          style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}
        >
          Download
        </button>
        <button
          onClick={onClose}
          className="rounded-md px-2 py-1 text-xs transition-colors hover:opacity-80"
          style={{ color: 'var(--text-muted)' }}
        >
          ✕
        </button>
      </div>
    </div>
  )
}
