import { Card, Spinner } from '@blueprintjs/core'

const SIGNAL_ICONS = {
  star:     { icon: '★', cls: 'signal-icon-star',    badgeCls: 'badge-star',     label: 'Starred' },
  fork:     { icon: '⑂', cls: 'signal-icon-fork',    badgeCls: 'badge-fork',     label: 'Forked' },
  new_repo: { icon: '◈', cls: 'signal-icon-new_repo', badgeCls: 'badge-new_repo', label: 'New Repo' },
  push:     { icon: '↑', cls: 'signal-icon-push',    badgeCls: 'badge-push',     label: 'Pushed' },
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

function SignalCard({ signal }) {
  const meta = SIGNAL_ICONS[signal.signal_type] || SIGNAL_ICONS.push
  const topics = signal.repo_topics || []

  return (
    <Card className="signal-card bp5-dark" style={{ padding: '12px 14px' }}>
      <div className="signal-row">
        <div className={`signal-icon-wrap ${meta.cls}`}>
          <span style={{ fontSize: 14 }}>{meta.icon}</span>
        </div>

        <div className="signal-content">
          <div className="signal-repo-name">
            <a href={signal.repo_url} target="_blank" rel="noreferrer">
              {signal.repo_name}
            </a>
          </div>
          {signal.repo_description && (
            <div className="signal-desc">{signal.repo_description}</div>
          )}
          <div className="signal-meta">
            <span className={`signal-type-badge ${meta.badgeCls}`}>{meta.label}</span>
            {signal.repo_language && (
              <span className="lang-tag">{signal.repo_language}</span>
            )}
            <span className="signal-engineer">@{signal.engineer_username}</span>
            <span className="lang-tag">{timeAgo(signal.detected_at)}</span>
            {topics.slice(0, 3).map((t, i) => (
              <span key={i} className="topic-tag">{t}</span>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

export default function SignalFeed({ signals, loading }) {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
        <Spinner size={24} />
      </div>
    )
  }

  if (!signals || signals.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40, fontSize: 13 }}>
        No signals yet. Run a sync to collect GitHub activity.
      </div>
    )
  }

  return (
    <div>
      {signals.map(s => <SignalCard key={s.id} signal={s} />)}
    </div>
  )
}
