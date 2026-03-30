'use client'

/** Three bouncing dots — agent thinking indicator */
export function StreamingDots() {
  return (
    <div className="mb-3 flex justify-start">
      <div className="flex gap-1 rounded-2xl px-4 py-3" style={{ background: 'var(--bg-secondary)' }}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block h-2 w-2 rounded-full animate-bounce"
            style={{
              background: 'var(--accent)',
              animationDelay: `${i * 100}ms`,
              animationDuration: '0.6s',
            }}
          />
        ))}
      </div>
    </div>
  )
}
