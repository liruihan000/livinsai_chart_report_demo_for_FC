'use client'

import { useState } from 'react'
import type { ToolStep } from '@/lib/types'

interface ToolStepsProps {
  steps: ToolStep[]
}

/** Icon for each tool type */
function ToolIcon({ name }: { name: string }) {
  if (name === 'query_database') {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
        <path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" />
      </svg>
    )
  }
  if (name === 'execute_code') {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    )
  }
  // load_skill or default
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 19.5v-15A2.5 2.5 0 016.5 2H20v20H6.5a2.5 2.5 0 010-5H20" />
    </svg>
  )
}

/** Spinning indicator for running step */
function Spinner() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="animate-spin"
      style={{ color: 'var(--text-muted)' }}
    >
      <path d="M21 12a9 9 0 11-6.219-8.56" />
    </svg>
  )
}

/** Checkmark for completed step */
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" style={{ color: 'var(--success)' }} />
    </svg>
  )
}

export function ToolSteps({ steps }: ToolStepsProps) {
  const [expanded, setExpanded] = useState(false)

  if (steps.length === 0) return null

  const allDone = steps.every((s) => s.status === 'done')
  const currentStep = steps.find((s) => s.status === 'running')

  return (
    <div className="mb-3" style={{ fontSize: '13px' }}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 transition-colors"
        style={{ color: 'var(--text-secondary)', cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}
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
        {allDone ? (
          <span>完成 {steps.length} 个步骤</span>
        ) : (
          <span>
            {currentStep ? currentStep.label : '处理中'}
            {currentStep?.name === 'execute_code' && (
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                {' '}(生成图表/报告，可能需要 10-30 秒)
              </span>
            )}
            {currentStep?.name !== 'execute_code' && (
              <span style={{ color: 'var(--text-muted)' }}>
                {' '}({steps.filter((s) => s.status === 'done').length}/{steps.length})
              </span>
            )}
          </span>
        )}
        {!allDone && <Spinner />}
      </button>

      {expanded && (
        <div className="mt-2 ml-1" style={{ borderLeft: '2px solid var(--border-light)', paddingLeft: '12px' }}>
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
                className="flex items-start gap-2"
                style={{ color: step.status === 'done' ? 'var(--text-secondary)' : 'var(--text-primary)' }}
              >
                <span className="mt-0.5 shrink-0">
                  {step.status === 'running' ? <Spinner /> : <CheckIcon />}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <ToolIcon name={step.name} />
                    <span style={{ fontWeight: 500 }}>{step.label}</span>
                  </div>
                  {step.input && (
                    <div
                      className="mt-1 overflow-hidden text-ellipsis"
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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
