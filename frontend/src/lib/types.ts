/** Chat message stored in localStorage and sent to API */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** File reference returned by the agent (Code Execution output) */
export interface FileRef {
  file_id: string
  filename: string
}

/** POST /chat request body */
export interface ChatRequest {
  messages: ChatMessage[]
  session_id: string
}

/** POST /chat response body */
export interface ChatResponse {
  reply: string
  session_id: string
  files?: FileRef[]
}

/** Session state persisted in localStorage */
export interface SessionState {
  messages: ChatMessage[]
  sessionId: string
}
