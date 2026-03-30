import type { ChatMessage, ChatResponse } from './types'

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

/** GET /reports/{fileId} — fetch generated PDF as blob */
export async function fetchReport(fileId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/reports/${fileId}`)
  if (!res.ok) {
    throw new Error(`Report fetch failed: ${res.status}`)
  }
  return res.blob()
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
