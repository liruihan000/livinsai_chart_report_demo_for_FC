'use client'

import { PdfToolbar } from './PdfToolbar'

interface PdfPanelProps {
  pdfUrl: string | null
  onClose: () => void
  onDownload: () => void
}

/**
 * Right-side PDF preview panel.
 * Slides in when a report is generated.
 * TODO: Integrate @react-pdf-viewer/core for full rendering.
 */
export function PdfPanel({ pdfUrl, onClose, onDownload }: PdfPanelProps) {
  return (
    <div
      className="flex w-[40%] flex-col border-l"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}
    >
      <PdfToolbar onClose={onClose} onDownload={onDownload} />
      <div className="flex-1 overflow-auto p-4">
        {pdfUrl ? (
          // TODO: Replace iframe with @react-pdf-viewer/core Worker + Viewer
          <iframe src={pdfUrl} className="h-full w-full rounded-lg" title="PDF Preview" />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p style={{ color: 'var(--text-muted)' }}>Loading PDF...</p>
          </div>
        )}
      </div>
    </div>
  )
}
