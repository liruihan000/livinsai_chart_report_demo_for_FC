import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  // Static export — no SSR, no rewrites.
  // API requests go directly to NEXT_PUBLIC_API_URL (set in .env.local).
}

export default nextConfig
