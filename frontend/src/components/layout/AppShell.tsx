'use client'

import type { ReactNode } from 'react'

interface AppShellProps {
  children: ReactNode
}

/** Root layout shell — full viewport, flex column */
export function AppShell({ children }: AppShellProps) {
  return <div className="flex h-screen flex-col overflow-hidden">{children}</div>
}
