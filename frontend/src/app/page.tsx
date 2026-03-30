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

  // Auto-add files when agent returns them
  useEffect(() => {
    if (chat.files && chat.files.length > 0) {
      pdf.addFiles(chat.files)
    }
  }, [chat.files]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="flex flex-1 flex-col" style={{ maxWidth: pdf.isOpen ? '58%' : '100%' }}>
        <AppShell>
          <Header
            onClearHistory={() => { chat.clearHistory(); pdf.clearFiles() }}
            hasMessages={chat.messages.length > 0}
            hasFiles={pdf.hasFiles}
            isPanelOpen={pdf.isOpen}
            onTogglePanel={pdf.togglePanel}
          />
          <ChatContainer
            messages={chat.messages}
            isLoading={chat.isLoading}
            activeToolSteps={chat.activeToolSteps}
            thinkingText={chat.thinkingText}
            streamingContent={chat.streamingContent}
            onSendMessage={chat.sendMessage}
            onViewReport={async (fileId, filename) => {
              await pdf.addFiles([{ file_id: fileId, filename: filename || 'report.pdf' }])
            }}
          />
        </AppShell>
      </div>
      {pdf.isOpen && (
        <PdfPanel
          files={pdf.allFiles}
          onClose={pdf.closePanel}
          onDownloadFile={pdf.downloadFile}
        />
      )}
    </div>
  )
}
