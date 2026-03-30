'use client'

import { useEffect } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Header } from '@/components/layout/Header'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { PdfPanel } from '@/components/pdf/PdfPanel'
import { useChat } from '@/hooks/useChat'
import { usePdf } from '@/hooks/usePdf'

export default function Home() {
  const chat = useChat()
  const pdf = usePdf()

  // Auto-open PDF panel when agent returns files
  useEffect(() => {
    if (chat.files && chat.files.length > 0) {
      const first = chat.files[0]
      pdf.openPdf(first.file_id, first.filename)
    }
  }, [chat.files]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AppShell>
      <Header onClearHistory={chat.clearHistory} />
      <main className="flex flex-1 overflow-hidden">
        <ChatContainer
          messages={chat.messages}
          isLoading={chat.isLoading}
          onSendMessage={chat.sendMessage}
          onViewReport={pdf.openPdf}
        />
        {pdf.isOpen && (
          <PdfPanel
            pdfUrl={pdf.pdfUrl}
            onClose={pdf.closePdf}
            onDownload={pdf.downloadPdf}
          />
        )}
      </main>
    </AppShell>
  )
}
