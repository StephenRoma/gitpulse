import { Spinner } from '@blueprintjs/core'

const SIGNAL_ICONS   = { star: '\u2605', fork: '\u2482', new_repo: '\u25C8', push: '\u2191' }
const SIGNAL_ACTIONS = { star: 'starred', fork: 'forked', new_repo: 'created repo', push: 'pushed to' }

function sigHeat(signal) {
  try {
    const score = JSON.parse(signal.raw_data || '{}').sig_score || 0
    return score >= 6 ? 'hot' : score >= 3 ? 'warm' : 'cool'
  } catch { return 'cool' }
}

const heatFg = (h) => h === 'hot' ? '#C8005A' : h === 'warm' ? '#D97706' : '#2563EB'
const heatBg = (h) => h === 'hot' ? '#FFF0F5' : h === 'warm' ? '#FFFBEB' : '#EFF6FF'
const heatBd = (h) => h === 'hot' ? '#FBCFE8' : h === 'warm' ? '#FDE68A' : '#BFDBFE'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr + (dateStr.endsWith('Z') ? '' : 'Z')).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function SignalFeed({ signals, loading }) {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
        <Spinner size={24} />
      </div>
    )
  }

  if (!signals?.length) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40, fontSize: 13, fontFamily: 'var(--mono)' }}>
        No signals yet. Run a sync to collect GitHub activity.
      </div>
    )
  }

  return (
    <div>
      <div className="signal-feed-header">
        <span style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', fontFamily: 'var(--mono)' }}>
          RECENT ACTIVITY &mdash; {signals.length} EVENTS
        </span>
        <div className="signal-heat-filters">
          {['hot', 'warm', 'cool'].map(h => (
            <span key={h} className="signal-heat-chip" style={{
              color: heatFg(h), background: heatBg(h), borderColor: heatBd(h),
            }}>{h.toUpperCase()}</span>
          ))}
        </div>
      </div>

      {signals.map(s => {
        const heat   = sigHeat(s)
        const icon   = SIGNAL_ICONS[s.signal_type]   || '\u00B7'
        const action = SIGNAL_ACTIONS[s.signal_type] || s.signal_type
        return (
          <div key={s.id} className="signal-row">
            <div className="signal-icon-box" style={{
              color: heatFg(heat), background: heatBg(heat), borderColor: heatBd(heat),
            }}>{icon}</div>
            <div className="signal-user">@{s.engineer_username}</div>
            <div style={{ flex: 1, fontSize: 11 }}>
              <span style={{ color: 'var(--text-faint)' }}>{action} </span>
              <a href={s.repo_url} target="_blank" rel="noreferrer"
                style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', fontSize: 11 }}>
                {s.repo_name}
              </a>
              {s.repo_language && (
                <span style={{ marginLeft: 8, fontSize: 10, padding: '1px 6px', borderRadius: 4,
                  background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                  {s.repo_language}
                </span>
              )}
            </div>
            <div className="signal-heat-badge" style={{
              color: heatFg(heat), background: heatBg(heat), borderColor: heatBd(heat),
            }}>{heat.toUpperCase()}</div>
            <div className="signal-time">{timeAgo(s.detected_at)}</div>
          </div>
        )
      })}
    </div>
  )
}
