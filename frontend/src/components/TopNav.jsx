import logo from '../assets/logo.svg'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'texas',     label: '🤠 TX Screen' },
]

export default function TopNav({ page = 'texas', onPageChange }) {
  return (
    <div className="gp-topnav">
      <div className="gp-logo">
        <img src={logo} className="gp-logo-mark" alt="Quorum" />
      </div>

      <div className="gp-nav-pills">
        {NAV_ITEMS.map(item => (
          <button
            key={item.key}
            className={`gp-nav-pill${page === item.key ? ' active' : ''}`}
            onClick={() => onPageChange?.(item.key)}
          >{item.label}</button>
        ))}
      </div>

      <div className="gp-nav-right">
        <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)', padding: '0 12px' }}>
          Babbage Sales Intelligence
        </div>
      </div>
    </div>
  )
}
