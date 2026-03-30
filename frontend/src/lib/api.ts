import type { ChatMessage, ChatResponse, FileRef } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** POST /chat — send full message history, receive agent reply */
export async function chatRequest(
  messages: ChatMessage[],
  sessionId: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, session_id: sessionId }),
  })
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`)
  }
  return res.json()
}

/** Callbacks for SSE stream events */
export interface StreamCallbacks {
  onSession: (sessionId: string) => void
  onThinking: (content: string) => void
  onToolStart: (name: string, label: string, input: string) => void
  onToolEnd: (name: string) => void
  onToken: (content: string) => void
  onDone: (files: FileRef[]) => void
  onError: (detail: string) => void
}

/** POST /chat/stream — SSE streaming with tool call steps */
export async function chatStream(
  messages: ChatMessage[],
  sessionId: string,
  callbacks: StreamCallbacks,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      session_id: sessionId,
    }),
  })
  if (!res.ok) {
    throw new Error(`Chat stream failed: ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE events from buffer
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      if (!part.trim()) continue
      let eventType = ''
      let data = ''
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (!eventType || !data) continue

      try {
        const parsed = JSON.parse(data)
        switch (eventType) {
          case 'session':
            callbacks.onSession(parsed.session_id)
            break
          case 'thinking':
            callbacks.onThinking(parsed.content)
            break
          case 'tool_start':
            callbacks.onToolStart(parsed.name, parsed.label, parsed.input)
            break
          case 'tool_end':
            callbacks.onToolEnd(parsed.name)
            break
          case 'token':
            callbacks.onToken(parsed.content)
            break
          case 'done':
            callbacks.onDone(parsed.files || [])
            break
          case 'error':
            callbacks.onError(parsed.detail)
            break
        }
      } catch {
        // skip malformed events
      }
    }
  }
}

export interface FetchedFile {
  blob: Blob
  contentType: string
}

/** GET /reports/{fileId} — fetch generated file as blob with content type */
export async function fetchReport(fileId: string): Promise<FetchedFile> {
  const res = await fetch(`${API_BASE}/reports/${fileId}`)
  if (!res.ok) {
    throw new Error(`Report fetch failed: ${res.status}`)
  }
  const blob = await res.blob()
  const contentType = res.headers.get('content-type') || blob.type || 'application/octet-stream'
  return { blob, contentType }
}

/** GET /health — check backend availability */
export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}
