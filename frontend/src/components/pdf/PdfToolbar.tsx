'use client'

interface PdfToolbarProps {
  title: string
  onClose: () => void
  checkedCount: number
  onDownloadChecked: () => void
}

export function PdfToolbar({
  title,
  onClose,
  checkedCount,
  onDownloadChecked,
}: PdfToolbarProps) {
  return (
    <div
      className="flex items-center justify-between gap-2 px-4 py-3"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
        {title}
      </span>
      <div className="flex shrink-0 items-center gap-2">
        {checkedCount > 0 && (
          <button
            onClick={onDownloadChecked}
            className="text-xs transition-colors"
            style={{
              color: 'var(--bg-secondary)',
              background: 'var(--accent)',
              padding: '3px 10px',
              borderRadius: '14px',
            }}
          >
            下载选中 ({checkedCount})
          </button>
        )}
        <button
          onClick={onClose}
          className="text-sm transition-colors"
          style={{ color: 'var(--text-muted)', padding: '2px 4px' }}
        >
          ✕
        </button>
      </div>
    </div>
  )
}
