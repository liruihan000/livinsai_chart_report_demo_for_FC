'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ToolSteps } from './ToolSteps'
import type { ChatMessage, ToolStep } from '@/lib/types'

interface MessageBubbleProps {
  message: ChatMessage
  onViewReport: (fileId: string, filename?: string) => Promise<void>
}

function AssistantAvatar() {
  return (
    <div
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
      style={{ background: '#e8e3db' }}
    >
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9b9690" strokeWidth="1.8">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>
  )
}

/** Collapsed thinking & tool steps for completed messages */
function CollapsedSteps({ steps }: { steps: ToolStep[] }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mb-2" style={{ fontSize: '13px' }}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 transition-colors"
        style={{
          color: 'var(--text-muted)',
          cursor: 'pointer',
          background: 'none',
          border: 'none',
          padding: 0,
        }}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.15s ease',
          }}
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span>{steps.length} 个步骤</span>
      </button>

      {expanded && (
        <div
          className="mt-2 ml-1"
          style={{ borderLeft: '2px solid var(--border-light)', paddingLeft: '12px' }}
        >
          {steps.map((step, i) => (
            <div key={i} className="py-1.5">
              {step.thinking && (
                <div
                  className="mb-1 text-sm italic"
                  style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}
                >
                  {step.thinking}
                </div>
              )}
              <div
                className="flex items-center gap-1.5"
                style={{ color: 'var(--text-secondary)' }}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  style={{ color: 'var(--success)' }}
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span style={{ fontWeight: 500 }}>{step.label}</span>
              </div>
              {step.input && (
                <div
                  className="mt-0.5 ml-5"
                  style={{
                    fontFamily: 'var(--font-mono), monospace',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    maxHeight: '60px',
                    overflow: 'hidden',
                  }}
                >
                  {step.input}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function MessageBubble({ message, onViewReport }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="mb-7 flex justify-end animate-fade-up">
        <div
          className="px-4 py-2.5 text-sm"
          style={{
            background: 'var(--accent-subtle)',
            borderRadius: 'var(--radius-bubble)',
            borderBottomRightRadius: '5px',
            maxWidth: '62%',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="mb-7 flex gap-3 animate-fade-up">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-col gap-1.5">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Report Agent
        </span>
        {message.toolSteps && message.toolSteps.length > 0 && (
          <CollapsedSteps steps={message.toolSteps} />
        )}
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

/** In-flight assistant message (streaming) with thinking, tool steps, and partial content */
export function StreamingMessage({
  toolSteps,
  thinkingText,
  content,
}: {
  toolSteps: ToolStep[]
  thinkingText: string
  content: string
}) {
  return (
    <div className="mb-7 flex gap-3 animate-fade-up">
      <AssistantAvatar />
      <div className="flex min-w-0 flex-col gap-1.5">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Report Agent
        </span>
        {thinkingText && (
          <div
            className="text-sm italic"
            style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}
          >
            <span
              className="mr-1.5 inline-block not-italic text-xs font-medium"
              style={{
                color: 'var(--text-secondary)',
                background: 'var(--border-light)',
                padding: '1px 6px',
                borderRadius: '4px',
              }}
            >
              Thinking
            </span>
            {thinkingText}
          </div>
        )}
        {toolSteps.length > 0 && <ToolSteps steps={toolSteps} />}
        {content ? (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex items-center gap-1 pt-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="inline-block h-1.5 w-1.5 rounded-full animate-bounce"
                style={{
                  background: 'var(--text-muted)',
                  animationDelay: `${i * 150}ms`,
                  animationDuration: '1.3s',
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
