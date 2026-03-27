import { Navbar, Button, Spinner, Tooltip, Intent } from '@blueprintjs/core'
import { useState } from 'react'
import { api } from '../api'

export default function TopNav({ onSyncAll, onAddAccount, apiHealth }) {
  const [syncing, setSyncing] = useState(false)

  async function handleSyncAll() {
    setSyncing(true)
    try {
      await api.syncAll()
      onSyncAll?.()
    } finally {
      setTimeout(() => setSyncing(false), 2000)
    }
  }

  return (
    <Navbar className="bp5-dark gp-topnav">
      <Navbar.Group align="left">
        <div className="gp-logo">
          <div className="gp-logo-mark">⚡</div>
          GitPulse
          <span className="gp-logo-sub">by Relevantz</span>
        </div>
      </Navbar.Group>

      <Navbar.Group align="right" style={{ gap: 12 }}>
        {apiHealth && (
          <div className="nav-status">
            <div className="nav-status-dot" />
            API Connected
          </div>
        )}

        <Button
          icon="refresh"
          text={syncing ? 'Syncing…' : 'Sync All'}
          intent={Intent.NONE}
          minimal
          loading={syncing}
          onClick={handleSyncAll}
          className="bp5-dark"
          style={{ color: 'var(--text-secondary)' }}
        />

        <Button
          icon="plus"
          text="Add Account"
          intent={Intent.PRIMARY}
          onClick={onAddAccount}
        />
      </Navbar.Group>
    </Navbar>
  )
}
