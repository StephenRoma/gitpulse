import { useState } from 'react'
import { Spinner } from '@blueprintjs/core'
import AccountLogo from './AccountLogo'

const STAGES = [
  { key: 'prospecting',  label: 'Prospecting',  color: '#2563EB', bg: '#EFF6FF', bd: '#BFDBFE' },
  { key: 'researched',   label: 'Researched',   color: '#0369A1', bg: '#E0F2FE', bd: '#BAE6FD' },
  { key: 'engaged',      label: 'Engaged',      color: '#D97706', bg: '#FFFBEB', bd: '#FDE68A' },
  { key: 'proposal',     label: 'Proposal',     color: '#7C3AED', bg: '#F5F3FF', bd: '#DDD6FE' },
  { key: 'partnership',  label: 'Partnership',  color: '#166534', bg: '#F0FDF4', bd: '#BBF7D0' },
]
const STAGE_KEYS  = STAGES.map(s => s.key)
const STAGE_MAP   = Object.fromEntries(STAGES.map(s => [s.key, s]))
const LOST_STYLE  = { color: '#B91C1C', bg: '#FFF1F2', bd: '#FECDD3' }

const SIGNAL_ICONS = {
  star: '★', fork: '⑂', new_repo: '◈', push: '↑',
  issue_comment: '💬', release: '🏷', org_issue: '⚠', hn_mention: '◎',
}

const CERTAINTY_STYLES = {
  confirmed:  { fg: '#166534', bg: '#F0FDF4', bd: '#BBF7D0' },
  active:     { fg: '#0369A1', bg: '#EFF6FF', bd: '#BFDBFE' },
  evaluating: { fg: '#92400E', bg: '#FFFBEB', bd: '#FDE68A' },
}

function scoreFg(s) { return s >= 85 ? '#C8005A' : s >= 60 ? '#D97706' : '#2563EB' }
function scoreBg(s) { return s >= 85 ? '#FFF0F5' : s >= 60 ? '#FFFBEB' : '#EFF6FF' }
function scoreBd(s) { return s >= 85 ? '#FBCFE8' : s >= 60 ? '#FDE68A' : '#BFDBFE' }

function initials(name) {
  if (!name) return '??'
  const p = name.trim().split(/\s+/)
  return p.length >= 2 ? (p[0][0] + p[p.length - 1][0]).toUpperCase() : name.slice(0, 2).toUpperCase()
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr + (dateStr.endsWith('Z') ? '' : 'Z')).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const PALETTE = ['#C8005A','#1A6B9A','#2D6A4F','#6D3A9C','#B85042','#D97706','#0369A1','#374060']

function accountColor(name) {
  let n = 0
  for (let i = 0; i < (name || '').length; i++) n += name.charCodeAt(i)
  return PALETTE[n % PALETTE.length]
}

// ─── Account card ─────────────────────────────────────────────────────────────
function AccountCard({ account, stage, onAdvance, onRetreat, onOpen }) {
  const score  = account.signal_score ?? 0
  const stageObj = STAGE_MAP[stage] || STAGES[0]
  const isLost = account._lost

  return (
    <div
      onClick={() => onOpen(account.id)}
      style={{
        background: '#fff',
        border: `1px solid ${isLost ? LOST_STYLE.bd : stageObj.bd}`,
        borderRadius: 8,
        padding: '10px 12px',
        cursor: 'pointer',
        marginBottom: 6,
        transition: 'box-shadow 0.15s',
        position: 'relative',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 10px rgba(0,0,0,0.08)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <AccountLogo account={account} size={28} radius={7} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 11, fontWeight: 700, color: isLost ? 'var(--text-muted)' : 'var(--navy)',
            fontFamily: 'var(--display)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>{account.name}</div>
          {account.district_domain && (
            <div style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
              {account.district_domain}
            </div>
          )}
        </div>
        <div style={{
          fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
          color: scoreFg(score), background: scoreBg(score), border: `1px solid ${scoreBd(score)}`,
          fontFamily: 'var(--mono)', flexShrink: 0,
        }}>{score}</div>
      </div>

      {/* Stage move arrows */}
      <div
        style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={() => onRetreat(account.id)}
          disabled={!onRetreat}
          title="Move back"
          style={{
            fontSize: 10, padding: '2px 6px', borderRadius: 4, cursor: 'pointer',
            border: '1px solid var(--border)', background: 'transparent',
            color: 'var(--text-faint)', lineHeight: 1,
            opacity: onRetreat ? 1 : 0.25,
          }}
        >←</button>
        <button
          onClick={() => onAdvance(account.id)}
          disabled={!onAdvance}
          title="Move forward"
          style={{
            fontSize: 10, padding: '2px 6px', borderRadius: 4, cursor: 'pointer',
            border: '1px solid var(--border)', background: 'transparent',
            color: 'var(--text-faint)', lineHeight: 1,
            opacity: onAdvance ? 1 : 0.25,
          }}
        >→</button>

            {stage === 'partnership' && (
          <button
            onClick={() => onAdvance(account.id, !account._lost)}
            title={account._lost ? 'Mark as Active' : 'Mark as Churned'}
            style={{
              fontSize: 9, padding: '2px 6px', borderRadius: 4, cursor: 'pointer',
              border: `1px solid ${account._lost ? '#BBF7D0' : '#FECDD3'}`,
              background: account._lost ? '#F0FDF4' : '#FFF1F2',
              color: account._lost ? '#166534' : '#B91C1C',
              fontFamily: 'var(--mono)', lineHeight: 1,
            }}
          >{account._lost ? 'ACTIVE' : 'CHURNED'}</button>
        )}
      </div>
    </div>
  )
}

// ─── Hot signal row ────────────────────────────────────────────────────────────
function HotSignalRow({ signal, onAccountClick }) {
  let raw = {}
  try { raw = JSON.parse(signal.raw_data || '{}') } catch {}
  const score     = raw.sig_score || 0
  const certainty = raw.certainty || 'evaluating'
  const certStyle = CERTAINTY_STYLES[certainty] || CERTAINTY_STYLES.evaluating
  const heat      = score >= 6 ? 'hot' : score >= 3 ? 'warm' : 'cool'
  const heatFg    = heat === 'hot' ? '#C8005A' : heat === 'warm' ? '#D97706' : '#2563EB'
  const heatBg    = heat === 'hot' ? '#FFF0F5' : heat === 'warm' ? '#FFFBEB' : '#EFF6FF'
  const heatBd    = heat === 'hot' ? '#FBCFE8' : heat === 'warm' ? '#FDE68A' : '#BFDBFE'

  const icon   = SIGNAL_ICONS[signal.signal_type] || '·'
  const detail = (raw.issue_title || signal.repo_description || '').slice(0, 70)

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '8px 12px', borderBottom: '1px solid var(--border)',
      fontSize: 11,
    }}>
      {/* Heat */}
      <div style={{
        fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 3,
        color: heatFg, background: heatBg, border: `1px solid ${heatBd}`,
        fontFamily: 'var(--mono)', whiteSpace: 'nowrap', flexShrink: 0,
      }}>{heat.toUpperCase()}</div>

      {/* Certainty */}
      <div style={{
        fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 3,
        color: certStyle.fg, background: certStyle.bg, border: `1px solid ${certStyle.bd}`,
        fontFamily: 'var(--mono)', whiteSpace: 'nowrap', flexShrink: 0,
      }}>{certainty.toUpperCase()}</div>

      {/* Type icon */}
      <span style={{ fontSize: 13, flexShrink: 0 }}>{icon}</span>

      {/* Account chip */}
      <span
        onClick={(e) => { e.stopPropagation(); onAccountClick(signal.account_id) }}
        style={{
          fontSize: 9, padding: '2px 7px', borderRadius: 10, cursor: 'pointer',
          background: accountColor(signal.account_name) + '18',
          border: `1px solid ${accountColor(signal.account_name)}40`,
          color: accountColor(signal.account_name),
          fontFamily: 'var(--mono)', fontWeight: 700, flexShrink: 0, whiteSpace: 'nowrap',
        }}
      >{signal.account_name}</span>

      {/* Engineer */}
      <span style={{ color: 'var(--text-faint)', fontFamily: 'var(--mono)', flexShrink: 0 }}>
        @{signal.engineer_username}
      </span>

      {/* Repo + detail */}
      <span style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', flexShrink: 0 }}>
        {signal.repo_name}
      </span>
      {detail && (
        <span style={{ color: 'var(--text-secondary)', flex: 1, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {detail}
        </span>
      )}

      <span style={{ color: 'var(--text-faint)', fontFamily: 'var(--mono)',
        fontSize: 10, flexShrink: 0, marginLeft: 'auto', paddingLeft: 8 }}>
        {timeAgo(signal.detected_at)}
      </span>
    </div>
  )
}

// ─── Main Dashboard ────────────────────────────────────────────────────────────
export default function DashboardPage({ accounts = [], stages = {}, onSetStage, hotSignals = [], hotLoading = false, onSelectAccount, onSyncAll }) {
  const [syncing, setSyncing] = useState(false)

  // Place each account into its stage, defaulting to 'prospecting'
  const columns = STAGES.map(s => ({
    ...s,
    accounts: accounts.filter(a => (stages[a.id] || 'prospecting') === s.key),
  }))

  function advance(accountId) {
    const cur = stages[accountId] || 'prospecting'
    const idx = STAGE_KEYS.indexOf(cur)
    if (idx < STAGE_KEYS.length - 1) onSetStage(accountId, STAGE_KEYS[idx + 1])
  }
  function retreat(accountId) {
    const cur = stages[accountId] || 'prospecting'
    const idx = STAGE_KEYS.indexOf(cur)
    if (idx > 0) onSetStage(accountId, STAGE_KEYS[idx - 1])
  }

  const totalAccounts  = accounts.length
  const activeAccounts = accounts.filter(a => {
    const s = stages[a.id] || 'prospecting'
    return s !== 'partnership'
  }).length
  const hotCount = accounts.filter(a => (a.signal_score ?? 0) >= 60).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Summary bar ─────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 12, padding: '14px 24px',
        borderBottom: '1px solid var(--border)', background: 'var(--surface)', flexShrink: 0,
      }}>
        {[
          { label: 'TOTAL ACCOUNTS',  value: totalAccounts },
          { label: 'ACTIVE PIPELINE', value: activeAccounts },
          { label: 'HOT ACCOUNTS',    value: hotCount },
        ].map(m => (
          <div key={m.label} style={{
            padding: '8px 16px', borderRadius: 8, background: 'var(--bg)',
            border: '1px solid var(--border)', minWidth: 100,
          }}>
            <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)',
              letterSpacing: '0.1em', marginBottom: 3 }}>{m.label}</div>
            <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--display)',
              color: 'var(--navy)' }}>{m.value}</div>
          </div>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          <button
            onClick={async () => {
              if (syncing || !onSyncAll) return
              setSyncing(true)
              try { await onSyncAll() } finally { setSyncing(false) }
            }}
            disabled={syncing}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 16px', borderRadius: 8, cursor: syncing ? 'not-allowed' : 'pointer',
              background: 'var(--navy)', color: '#fff', border: 'none',
              fontSize: 11, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.06em',
              opacity: syncing ? 0.7 : 1,
            }}
          >
            {syncing ? <Spinner size={12} /> : '↻'}
            {syncing ? 'SCANNING...' : 'SCAN ALL'}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 28 }}>

        {/* ── Pipeline kanban ─────────────────────────────────────────────── */}
        <div>
          <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700,
            letterSpacing: '0.12em', color: 'var(--text-faint)', marginBottom: 12 }}>
            PIPELINE STAGES
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, alignItems: 'start' }}>
            {columns.map((col, colIdx) => (
              <div key={col.key}>
                {/* Column header */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
                  padding: '5px 8px', borderRadius: 6,
                  background: col.bg, border: `1px solid ${col.bd}`,
                }}>
                  <span style={{
                    fontFamily: 'var(--display)', fontWeight: 700, fontSize: 10,
                    color: col.color, flex: 1,
                  }}>{col.label.toUpperCase()}</span>
                  <span style={{
                    fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700,
                    color: col.color, background: col.bg,
                  }}>{col.accounts.length}</span>
                </div>

                {/* Account cards */}
                {col.accounts.length === 0 ? (
                  <div style={{
                    padding: '16px 10px', textAlign: 'center', fontSize: 10,
                    color: 'var(--text-faint)', fontFamily: 'var(--mono)',
                    border: '1px dashed var(--border)', borderRadius: 8,
                  }}>—</div>
                ) : (
                  col.accounts.map(a => (
                    <AccountCard
                      key={a.id}
                      account={a}
                      stage={col.key}
                      onAdvance={colIdx < STAGES.length - 1 ? advance : null}
                      onRetreat={colIdx > 0 ? retreat : null}
                      onOpen={(id) => onSelectAccount(id)}
                    />
                  ))
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Hot signals feed ─────────────────────────────────────────────── */}
        <div>
          <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700,
            letterSpacing: '0.12em', color: 'var(--text-faint)', marginBottom: 12 }}>
            PRIORITY SIGNALS ACROSS ALL ACCOUNTS
          </div>
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden',
          }}>
            {hotLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
                <Spinner size={20} />
              </div>
            ) : hotSignals.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', fontSize: 12,
                color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                No signals yet. Run a Scan to start collecting district signals.
              </div>
            ) : (
              hotSignals.map((sig, i) => (
                <HotSignalRow
                  key={`${sig.id}-${i}`}
                  signal={sig}
                  onAccountClick={(id) => onSelectAccount(id)}
                />
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
