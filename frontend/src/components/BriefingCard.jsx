import { Spinner } from '@blueprintjs/core'

export default function BriefingCard({ briefing, loading, onRegenerate, onOutreach }) {
  const content = briefing?.content

  return (
    <div className="briefing-card">
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div className="briefing-icon">&diams;</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="briefing-label">AI BRIEFING</span>
              {content?.urgency && (
                <span style={{
                  padding: '1px 7px', borderRadius: 4, fontSize: 9, fontWeight: 700,
                  letterSpacing: '0.06em',
                  color:      content.urgency === 'high' ? '#C8005A' : content.urgency === 'medium' ? '#D97706' : '#2563EB',
                  background: content.urgency === 'high' ? '#FFF0F5' : content.urgency === 'medium' ? '#FFFBEB' : '#EFF6FF',
                  border: `1px solid ${content.urgency === 'high' ? '#FBCFE8' : content.urgency === 'medium' ? '#FDE68A' : '#BFDBFE'}`,
                  fontFamily: 'var(--mono)',
                }}>{content.urgency.toUpperCase()}</span>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {briefing?.generated_at && (
                <span style={{ fontSize: 10, color: '#B0BCDA', fontFamily: 'var(--mono)' }}>
                  {new Date(briefing.generated_at + 'Z').toLocaleDateString()}
                </span>
              )}
              <button
                onClick={onRegenerate}
                disabled={loading}
                style={{
                  background: 'none', border: 'none',
                  cursor: loading ? 'default' : 'pointer',
                  color: 'var(--text-faint)', fontSize: 11, fontFamily: 'var(--mono)',
                  padding: '2px 6px', borderRadius: 4,
                }}
              >
                {loading ? <Spinner size={12} /> : 'Regenerate'}
              </button>
            </div>
          </div>

          {loading && !content ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-muted)' }}>
              <Spinner size={14} />
              <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>Analyzing signals...</span>
            </div>
          ) : content ? (
            <>
              <p className="briefing-text">{content.summary}</p>
              {content.key_themes?.length > 0 && (
                <div className="theme-chips">
                  {content.key_themes.map((t, i) => (
                    <span key={i} className="theme-chip">{t}</span>
                  ))}
                </div>
              )}
              {onOutreach && (
                <div style={{ marginTop: 12 }}>
                  <button onClick={onOutreach} style={{
                    padding: '5px 14px', borderRadius: 6, border: '1px solid #FBCFE8',
                    background: '#FFF0F5', color: 'var(--magenta)',
                    fontSize: 11, cursor: 'pointer', fontFamily: 'var(--mono)',
                  }}>Draft Outreach</button>
                </div>
              )}
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No briefing yet. Run a sync or click Regenerate.
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
