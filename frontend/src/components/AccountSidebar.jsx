import { Spinner } from '@blueprintjs/core'
import { useState } from 'react'
import AccountLogo from './AccountLogo'

const PALETTE = ['#C8005A','#1A6B9A','#2D6A4F','#6D3A9C','#B85042','#D97706','#0369A1','#374060']
const heatColor  = (s) => s >= 85 ? '#C8005A' : s >= 60 ? '#D97706' : '#2563EB'
const heatBg     = (s) => s >= 85 ? '#FFF0F5' : s >= 60 ? '#FFFBEB' : '#EFF6FF'
const heatBorder = (s) => s >= 85 ? '#FBCFE8' : s >= 60 ? '#FDE68A' : '#BFDBFE'
const heatLabel  = (s) => s >= 85 ? 'HOT'     : s >= 60 ? 'WARM'    : 'COOL'

function initials(name) {
  if (!name) return '??'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

export default function AccountSidebar({ accounts, selectedId, onSelect, onDelete, onEdit, onAdd, filter, onFilter }) {
  const [deletingId, setDeletingId] = useState(null)

  async function handleDelete(e, id) {
    e.stopPropagation()
    if (!confirm('Delete this account and all its signals?')) return
    setDeletingId(id)
    try { await onDelete(id) } finally { setDeletingId(null) }
  }

  const allAccounts = accounts
  const counts = {
    all:      allAccounts.length,
    client:   allAccounts.filter(a => a.account_type === 'client').length,
    prospect: allAccounts.filter(a => a.account_type === 'prospect').length,
  }

  return (
    <div className="gp-sidebar">
      <div className="sidebar-search">
        <div className="sidebar-search-inner">
          <span style={{ color: 'var(--text-faint)', fontSize: 13 }}>&#x2315;</span>
          <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>Search accounts...</span>
        </div>
      </div>

      <div className="sidebar-filters">
        {[
          { k: 'all',      l: 'All',      n: counts.all },
          { k: 'clients',  l: 'Partners', n: counts.client },
          { k: 'pipeline', l: 'Prospects', n: counts.prospect },
        ].map(f => (
          <button key={f.k}
            onClick={() => onFilter(f.k)}
            className={`sidebar-filter-btn${filter === f.k ? ' active' : ''}`}>
            {f.l}
            <span style={{ marginLeft: 4, fontSize: 9,
              color: filter === f.k ? '#C8005A' : 'var(--text-faint)' }}>{f.n}</span>
          </button>
        ))}
      </div>

      <div className="sidebar-section-label">ACCOUNTS &mdash; {accounts.length}</div>

      <div className="sidebar-list">
        {accounts.length === 0 && (
          <div style={{ padding: '20px 16px', color: 'var(--text-faint)', fontSize: 12, fontFamily: 'var(--mono)' }}>
            No accounts yet.
          </div>
        )}
        {accounts.map(acc => {
          const color = PALETTE[acc.id % PALETTE.length]
          const score = acc.signal_score || 0
          return (
            <div key={acc.id}
              className={`account-row${selectedId === acc.id ? ' active' : ''}`}
              style={{ borderLeftColor: selectedId === acc.id ? color : 'transparent' }}
              onClick={() => onSelect(acc.id)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <AccountLogo account={acc} size={36} radius={10} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                    <span style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--navy)' }}>
                      {acc.name || acc.district_domain}
                    </span>
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                      color: heatColor(score), background: heatBg(score),
                      border: `1px solid ${heatBorder(score)}`,
                      padding: '1px 6px', borderRadius: 4, fontFamily: 'var(--mono)',
                    }}>{heatLabel(score)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{
                      fontSize: 9, padding: '1px 7px', borderRadius: 4,
                      background: acc.account_type === 'client' ? '#E0F2FE' : '#F3E8FF',
                      color: acc.account_type === 'client' ? '#0369A1' : '#7C3AED',
                      border: `1px solid ${acc.account_type === 'client' ? '#BAE6FD' : '#DDD6FE'}`,
                      fontFamily: 'var(--mono)',
                    }}>{acc.account_type === 'client' ? 'Partner District' : 'Prospect'}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      {acc.district_domain
                        ? <span style={{ fontSize: 9, color: '#2D6A4F', background: '#D1FAE5', border: '1px solid #6EE7B7', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--mono)' }}>
                            {acc.district_domain}
                          </span>
                        : <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>no domain</span>
                      }
                      <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
                        {acc.signal_count || 0} signals
                      </span>
                    </div>
                  </div>
                  <div style={{ background: '#E8ECF8', borderRadius: 2, height: 3 }}>
                    <div style={{
                      width: `${Math.min(score, 100)}%`, height: '100%',
                      borderRadius: 2, background: heatColor(score), transition: 'width 0.3s',
                    }} />
                  </div>
                </div>
                <div style={{ marginLeft: 4, flexShrink: 0, display: 'flex', gap: 3, alignItems: 'center' }}>
                  {deletingId === acc.id
                    ? <Spinner size={12} />
                    : (
                      <>
                        <button className="acct-delete-btn"
                          style={{ background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-faint)', padding: '2px 4px', borderRadius: 4, opacity: 0, fontSize: 11 }}
                          title="Edit account"
                          onClick={e => { e.stopPropagation(); onEdit && onEdit(acc) }}>&#9998;</button>
                        <button className="acct-delete-btn"
                          style={{ background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-faint)', padding: '2px 4px', borderRadius: 4, opacity: 0, fontSize: 11 }}
                          onClick={e => handleDelete(e, acc.id)}>x</button>
                      </>
                    )
                  }
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="sidebar-footer">
        <span>{counts.client} active clients</span>
        <span>{counts.prospect} in pipeline</span>
      </div>
    </div>
  )
}
