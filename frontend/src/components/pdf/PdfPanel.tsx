'use client'

import { useState } from 'react'
import { PdfToolbar } from './PdfToolbar'
import type { FileRef } from '@/lib/types'

interface CachedFile {
  fileRef: FileRef
  blobUrl: string
}

interface PdfPanelProps {
  files: CachedFile[]
  onClose: () => void
  onDownloadFile: (index: number) => void
}

function isImageFile(filename: string): boolean {
  return /\.(png|jpe?g|svg|gif|webp)$/i.test(filename)
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="10" height="10" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
      style={{
        transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
        transition: 'transform 0.15s ease',
      }}
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

export function PdfPanel({
  files,
  onClose,
  onDownloadFile,
}: PdfPanelProps) {
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  // Track which files have their preview expanded
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleCheck = (fileId: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(fileId)) next.delete(fileId)
      else next.add(fileId)
      return next
    })
  }

  const toggleExpand = (fileId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(fileId)) next.delete(fileId)
      else next.add(fileId)
      return next
    })
  }

  const downloadChecked = () => {
    files.forEach((f, i) => {
      if (checkedIds.has(f.fileRef.file_id)) {
        onDownloadFile(i)
      }
    })
  }

  return (
    <div
      className="flex flex-col"
      style={{
        width: '42%',
        borderLeft: '1px solid var(--border)',
        background: 'var(--bg-secondary)',
      }}
    >
      <PdfToolbar
        title={`文件 (${files.length})`}
        onClose={onClose}
        checkedCount={checkedIds.size}
        onDownloadChecked={downloadChecked}
      />

      {/* File list with inline collapsible previews */}
      <div className="flex-1 overflow-y-auto">
        {files.map((f, i) => {
          const isExpanded = expandedIds.has(f.fileRef.file_id)
          const isImage = isImageFile(f.fileRef.filename)

          return (
            <div key={f.fileRef.file_id} style={{ borderBottom: '1px solid var(--border)' }}>
              {/* File row */}
              <div
                className="flex items-center gap-2 px-4 py-2.5"
                style={{ cursor: 'pointer' }}
              >
                <input
                  type="checkbox"
                  checked={checkedIds.has(f.fileRef.file_id)}
                  onChange={() => toggleCheck(f.fileRef.file_id)}
                  className="h-3.5 w-3.5 shrink-0 accent-[#9b9690]"
                  onClick={(e) => e.stopPropagation()}
                />
                <button
                  onClick={() => toggleExpand(f.fileRef.file_id)}
                  className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-xs"
                  style={{ color: 'var(--text-primary)' }}
                >
                  <ChevronIcon open={isExpanded} />
                  <span className="truncate">{f.fileRef.filename}</span>
                </button>
                <button
                  onClick={() => onDownloadFile(i)}
                  className="shrink-0 text-xs transition-colors"
                  style={{ color: 'var(--text-muted)', padding: '2px 6px' }}
                >
                  ↓
                </button>
              </div>

              {/* Inline preview (collapsible) */}
              {isExpanded && (
                <div className="px-4 pb-3">
                  {isImage ? (
                    <img
                      src={f.blobUrl}
                      alt={f.fileRef.filename}
                      className="w-full object-contain"
                      style={{ borderRadius: '6px', maxHeight: '400px' }}
                    />
                  ) : (
                    <iframe
                      src={f.blobUrl}
                      className="w-full"
                      style={{
                        height: '400px',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                      }}
                      title={f.fileRef.filename}
                    />
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
