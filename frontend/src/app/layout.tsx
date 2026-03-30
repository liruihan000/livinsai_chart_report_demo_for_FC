import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { displayFont, bodyFont, monoFont } from '@/config/fonts'
import './globals.css'

export const metadata: Metadata = {
  title: 'Livins Report Agent',
  description: 'Housing data analysis and report generation',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="zh-CN"
      className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable}`}
    >
      <body>
        {children}
      </body>
    </html>
  )
}
