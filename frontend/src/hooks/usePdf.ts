'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useLocalStorage } from './useLocalStorage'
import { fetchReport } from '@/lib/api'
import { STORAGE_KEYS } from '@/lib/storage'
import type { FileRef } from '@/lib/types'

export interface CachedFile {
  fileRef: FileRef
  blobUrl: string
}

/** Map content-type to correct file extension */
function fixExtension(filename: string, contentType: string): string {
  const extMap: Record<string, string> = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/svg+xml': '.svg',
    'application/pdf': '.pdf',
    'text/csv': '.csv',
    'text/markdown': '.md',
  }
  const correctExt = extMap[contentType]
  if (!correctExt) return filename

  const dotIndex = filename.lastIndexOf('.')
  const baseName = dotIndex > 0 ? filename.slice(0, dotIndex) : filename
  return baseName + correctExt
}

/** Deduplicate filenames by appending _1, _2, etc. */
function deduplicateFilename(filename: string, existing: string[]): string {
  if (!existing.includes(filename)) return filename
  const dotIndex = filename.lastIndexOf('.')
  const base = dotIndex > 0 ? filename.slice(0, dotIndex) : filename
  const ext = dotIndex > 0 ? filename.slice(dotIndex) : ''
  let n = 1
  while (existing.includes(`${base}_${n}${ext}`)) n++
  return `${base}_${n}${ext}`
}

export interface UsePdfReturn {
  allFiles: CachedFile[]
  activeIndex: number
  activeBlobUrl: string | null
  activeFilename: string
  isOpen: boolean
  hasFiles: boolean
  isRestoring: boolean
  addFiles: (files: FileRef[]) => Promise<void>
  selectFile: (index: number) => void
  togglePanel: () => void
  closePanel: () => void
  downloadActive: () => void
  downloadFile: (index: number) => void
  /** Clear all files and localStorage (called on clear history) */
  clearFiles: () => void
}

export function usePdf(): UsePdfReturn {
  const [allFiles, setAllFiles] = useState<CachedFile[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [isOpen, setIsOpen] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const filesRef = useRef<CachedFile[]>([])
  const restoredRef = useRef(false)

  // Persist file refs (file_id + filename) to localStorage
  const [savedFileRefs, setSavedFileRefs] = useLocalStorage<FileRef[]>(STORAGE_KEYS.FILES, [])

  // Restore files from localStorage on mount
  useEffect(() => {
    if (restoredRef.current || savedFileRefs.length === 0) return
    restoredRef.current = true

    const restore = async () => {
      setIsRestoring(true)
      const restored: CachedFile[] = []
      for (const ref of savedFileRefs) {
        try {
          const { blob } = await fetchReport(ref.file_id)
          const blobUrl = URL.createObjectURL(blob)
          restored.push({ fileRef: ref, blobUrl })
        } catch {
          // File no longer available on server, skip it
          console.warn(`Failed to restore file: ${ref.filename} (${ref.file_id})`)
        }
      }
      filesRef.current = restored
      setAllFiles([...restored])
      // Update localStorage to remove files that failed to restore
      if (restored.length !== savedFileRefs.length) {
        setSavedFileRefs(restored.map((c) => c.fileRef))
      }
      setIsRestoring(false)
    }
    restore()
  }, [savedFileRefs]) // eslint-disable-line react-hooks/exhaustive-deps

  const addFiles = useCallback(async (files: FileRef[]) => {
    const newCached: CachedFile[] = []
    for (const f of files) {
      if (filesRef.current.some((c) => c.fileRef.file_id === f.file_id)) continue

      const { blob, contentType } = await fetchReport(f.file_id)
      const blobUrl = URL.createObjectURL(blob)

      const fixedName = fixExtension(f.filename, contentType)
      const existingNames = [
        ...filesRef.current.map((c) => c.fileRef.filename),
        ...newCached.map((c) => c.fileRef.filename),
      ]
      const finalName = deduplicateFilename(fixedName, existingNames)

      newCached.push({
        fileRef: { file_id: f.file_id, filename: finalName },
        blobUrl,
      })
    }
    if (newCached.length > 0) {
      filesRef.current = [...filesRef.current, ...newCached]
      setAllFiles([...filesRef.current])
      setActiveIndex(filesRef.current.length - newCached.length)
      setIsOpen(true)
      // Persist to localStorage
      setSavedFileRefs(filesRef.current.map((c) => c.fileRef))
    }
  }, [setSavedFileRefs])

  const selectFile = useCallback((index: number) => {
    setActiveIndex(index)
  }, [])

  const togglePanel = useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  const closePanel = useCallback(() => {
    setIsOpen(false)
  }, [])

  const downloadFile = useCallback((index: number) => {
    const file = filesRef.current[index]
    if (!file) return
    const a = document.createElement('a')
    a.href = file.blobUrl
    a.download = file.fileRef.filename
    a.click()
  }, [])

  const downloadActive = useCallback(() => {
    downloadFile(activeIndex)
  }, [activeIndex, downloadFile])

  const clearFiles = useCallback(() => {
    // Revoke all blob URLs
    for (const f of filesRef.current) {
      URL.revokeObjectURL(f.blobUrl)
    }
    filesRef.current = []
    setAllFiles([])
    setActiveIndex(0)
    setIsOpen(false)
    setSavedFileRefs([])
  }, [setSavedFileRefs])

  const active = allFiles[activeIndex]

  return {
    allFiles,
    activeIndex,
    activeBlobUrl: active?.blobUrl ?? null,
    activeFilename: active?.fileRef.filename ?? 'report.pdf',
    isOpen,
    hasFiles: allFiles.length > 0,
    isRestoring,
    addFiles,
    selectFile,
    togglePanel,
    closePanel,
    downloadActive,
    downloadFile,
    clearFiles,
  }
}
