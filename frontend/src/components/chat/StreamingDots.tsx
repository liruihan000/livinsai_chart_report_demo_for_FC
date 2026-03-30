'use client'

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

export function StreamingDots() {
  return (
    <div className="mb-7 flex gap-3 animate-fade-up">
      <AssistantAvatar />
      <div className="flex items-center gap-1 pt-2">
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
    </div>
  )
}
