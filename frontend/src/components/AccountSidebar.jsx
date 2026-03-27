import { Button, Spinner, Tooltip, Intent, MenuItem, Menu, Popover } from '@blueprintjs/core'
import { useState } from 'react'
import { api } from '../api'

function scoreClass(score) {
  if (score >= 60) return 'high'
  if (score >= 25) return 'medium'
  return 'low'
}

function Initials({ name }) {
  const parts = name.split(' ')
  const init = parts.length >= 2
    ? parts[0][0] + parts[1][0]
    : name.slice(0, 2)
  return init.toUpperCase()
}

export default function AccountSidebar({ accounts, selectedId, onSelect, onRefresh }) {
  const [deletingId, setDeletingId] = useState(null)

  async function handleDelete(e, id) {
    e.stopPropagation()
    if (!confirm('Delete this account and all its signals?')) return
    setDeletingId(id)
    try {
      await api.deleteAccount(id)
      onRefresh()
    } finally {
      setDeletingId(null)
    }
  }

  const prospects = accounts.filter(a => a.account_type === 'prospect')
  const clients = accounts.filter(a => a.account_type === 'client')

  function renderGroup(label, items) {
    if (!items.length) return null
    return (
      <>
        <div className="sidebar-section-label">{label}</div>
        {items.map(account => (
          <div
            key={account.id}
            className={`account-item ${selectedId === account.id ? 'active' : ''}`}
            onClick={() => onSelect(account.id)}
          >
            <div className={`score-dot ${scoreClass(account.signal_score || 0)}`} />

            <div className="account-avatar">
              <Initials name={account.name} />
            </div>

            <div className="account-info">
              <div className="account-name">{account.name}</div>
              <div className="account-meta">
                {account.signal_count || 0} signals · {account.engineer_count || 0} eng
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div className="signal-badge">{account.signal_score || 0}</div>
              {deletingId === account.id
                ? <Spinner size={12} />
                : (
                  <Button
                    icon="trash"
                    minimal
                    small
                    style={{ color: 'var(--text-muted)', opacity: 0 }}
                    className="account-delete-btn"
                    onClick={(e) => handleDelete(e, account.id)}
                  />
                )
              }
            </div>
          </div>
        ))}
      </>
    )
  }

  return (
    <div className="gp-sidebar bp5-dark">
      <div className="sidebar-header">
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          {accounts.length} accounts tracked
        </span>
      </div>

      {accounts.length === 0 && (
        <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.6 }}>
          No accounts yet. Add a prospect or client to start tracking GitHub signals.
        </div>
      )}

      {renderGroup('Prospects', prospects)}
      {renderGroup('Clients', clients)}

      <style>{`
        .account-item:hover .account-delete-btn { opacity: 1 !important; }
      `}</style>
    </div>
  )
}
