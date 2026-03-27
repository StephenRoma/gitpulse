import { useState } from 'react'

export default function TopNav({ accounts = [], onAddAccount }) {
  const lastSynced = accounts.reduce((latest, a) => {
    if (!a.last_synced) return latest
    const d = new Date(a.last_synced)
    return d > latest ? d : latest
  }, new Date(0))

  const syncLabel = lastSynced.getTime() > 0
    ? `Synced ${lastSynced.toLocaleDateString()}`
    : 'No sync yet'

  return (
    <div className="gp-topnav">
      <div className="gp-logo">
        <div className="gp-logo-mark">G</div>
        <div className="gp-logo-name">Git<span>Pulse</span></div>
        <div className="gp-logo-beta">BETA</div>
      </div>

      <div className="gp-nav-pills">
        <button className="gp-nav-pill active">Dashboard</button>
        <button className="gp-nav-pill">Accounts</button>
        <button className="gp-nav-pill">Reports</button>
      </div>

      <div className="gp-nav-right">
        <div className="nav-live">
          <span className="nav-live-dot" />
          <span>{syncLabel}</span>
        </div>
        <div className="nav-divider" />
        <button className="nav-add-btn" onClick={onAddAccount}>+ Add Account</button>
        <div className="nav-avatar">RV</div>
      </div>
    </div>
  )
}
