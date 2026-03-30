'use client'

import { useState, useCallback, useRef } from 'react'
import { fetchReport } from '@/lib/api'

export interface UsePdfReturn {
  pdfUrl: string | null
  isOpen: boolean
  openPdf: (fileId: string, filename?: string) => Promise<void>
  closePdf: () => void
  downloadPdf: () => void
}

export function usePdf(): UsePdfReturn {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const blobUrlRef = useRef<string | null>(null)
  const filenameRef = useRef<string>('report.pdf')

  const openPdf = useCallback(async (fileId: string, filename?: string) => {
    // Revoke previous blob URL
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current)
    }

    filenameRef.current = filename || 'report.pdf'
    const blob = await fetchReport(fileId)
    const url = URL.createObjectURL(blob)
    blobUrlRef.current = url
    setPdfUrl(url)
    setIsOpen(true)
  }, [])

  const closePdf = useCallback(() => {
    setIsOpen(false)
  }, [])

  const downloadPdf = useCallback(() => {
    if (!blobUrlRef.current) return
    const a = document.createElement('a')
    a.href = blobUrlRef.current
    a.download = filenameRef.current
    a.click()
  }, [])

  return { pdfUrl, isOpen, openPdf, closePdf, downloadPdf }
}
