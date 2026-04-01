import logo from '../assets/logo.svg'

export default function TopNav({ accounts = [], onAddAccount, page = 'dashboard', onPageChange }) {
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
        <img src={logo} className="gp-logo-mark" alt="Temporality" />
      </div>

      <div className="gp-nav-pills">
        <button
          className={`gp-nav-pill${page === 'dashboard' ? ' active' : ''}`}
          onClick={() => onPageChange?.('dashboard')}
        >Dashboard</button>
        <button
          className={`gp-nav-pill${page === 'accounts' ? ' active' : ''}`}
          onClick={() => onPageChange?.('accounts')}
        >Accounts</button>
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
