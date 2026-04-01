import { useState } from 'react'

const PALETTE = ['#C8005A','#1A6B9A','#2D6A4F','#6D3A9C','#B85042','#D97706','#0369A1','#374060']

function initials(name) {
  if (!name) return '??'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function paletteColor(id, name) {
  // Prefer id-based palette for consistent color; fall back to name hash
  if (id != null) return PALETTE[id % PALETTE.length]
  let n = 0
  for (let i = 0; i < (name || '').length; i++) n += name.charCodeAt(i)
  return PALETTE[n % PALETTE.length]
}

/**
 * AccountLogo — renders company logo with three-tier fallback:
 *   1. GitHub org avatar (stored in account.avatar_url after sync)
 *   2. Clearbit logo from github_org slug (e.g. stripe.com)
 *   3. Letter initials fallback box
 *
 * Props:
 *   account   — the account object { id, name, github_org, avatar_url }
 *   size      — pixel size (default 36)
 *   radius    — border-radius (default 10)
 *   style     — extra style overrides
 */
export default function AccountLogo({ account = {}, size = 36, radius = 10, style = {} }) {
  const [githubFailed,   setGithubFailed]   = useState(false)
  const [clearbitFailed, setClearbitFailed] = useState(false)

  const color   = paletteColor(account.id, account.name)
  const baseStyle = {
    width: size, height: size,
    borderRadius: radius,
    flexShrink: 0,
    overflow: 'hidden',
    ...style,
  }

  // Tier 1: GitHub org avatar (populated after sync)
  if (account.avatar_url && !githubFailed) {
    return (
      <img
        src={account.avatar_url}
        alt={account.name}
        style={{ ...baseStyle, objectFit: 'cover', display: 'block' }}
        onError={() => setGithubFailed(true)}
      />
    )
  }

  // Tier 2: Clearbit logo from org slug → company domain guess
  const orgSlug = account.github_org
  if (orgSlug && !clearbitFailed) {
    return (
      <img
        src={`https://logo.clearbit.com/${orgSlug}.com`}
        alt={account.name}
        style={{ ...baseStyle, objectFit: 'contain', background: '#fff', display: 'block' }}
        onError={() => setClearbitFailed(true)}
      />
    )
  }

  // Tier 3: Letter initials fallback
  return (
    <div style={{
      ...baseStyle,
      background: color + '14',
      border: `1.5px solid ${color}28`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: Math.round(size * 0.3), fontWeight: 800, color,
      fontFamily: 'var(--display)',
    }}>
      {initials(account.name || account.github_org)}
    </div>
  )
}
