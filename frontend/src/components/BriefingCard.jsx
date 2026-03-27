import { Card, Button, Spinner, Intent, Tooltip, Tag } from '@blueprintjs/core'
import { useState } from 'react'
import { api } from '../api'

function UrgencyBadge({ level }) {
  return <span className={`urgency-badge urgency-${level}`}>{level} priority</span>
}

export default function BriefingCard({ accountId, briefing, onRefresh }) {
  const [generating, setGenerating] = useState(false)

  async function handleGenerate() {
    setGenerating(true)
    try {
      await api.generateBriefing(accountId)
      // Poll until done
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        const status = await api.getSyncStatus(accountId)
        if (status.status === 'done' || status.status === 'error' || attempts > 30) {
          clearInterval(poll)
          setGenerating(false)
          onRefresh()
        }
      }, 2000)
    } catch {
      setGenerating(false)
    }
  }

  const content = briefing?.content

  if (!content && !generating) {
    return (
      <Card className="briefing-card">
        <div className="briefing-header">
          <div className="briefing-label">
            <span>⚡</span> AI Intelligence Briefing
          </div>
          <Button
            icon="generate"
            text="Generate Briefing"
            intent={Intent.PRIMARY}
            small
            onClick={handleGenerate}
          />
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          No briefing generated yet. Run a sync or click Generate to create one.
        </div>
      </Card>
    )
  }

  if (generating) {
    return (
      <Card className="briefing-card">
        <div className="briefing-header">
          <div className="briefing-label"><span>⚡</span> AI Intelligence Briefing</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-muted)' }}>
          <Spinner size={16} />
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>Claude is analyzing signals…</span>
        </div>
      </Card>
    )
  }

  return (
    <Card className="briefing-card">
      <div className="briefing-header">
        <div className="briefing-label">
          <span>⚡</span> AI Intelligence Briefing
          {content.urgency && <UrgencyBadge level={content.urgency} />}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {briefing.generated_at && (
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-muted)' }}>
              {new Date(briefing.generated_at + 'Z').toLocaleDateString()}
            </span>
          )}
          <Button icon="refresh" minimal small onClick={handleGenerate} loading={generating}
            style={{ color: 'var(--text-muted)' }} />
        </div>
      </div>

      <div className="briefing-summary">{content.summary}</div>

      {content.key_themes?.length > 0 && (
        <div className="theme-chips">
          {content.key_themes.map((t, i) => (
            <div key={i} className="theme-chip">{t}</div>
          ))}
        </div>
      )}

      {content.opportunities?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
            Opportunities
          </div>
          {content.opportunities.map((opp, i) => (
            <div key={i} className="opportunity-item">
              <div className="opportunity-title">→ {opp.title}</div>
              <div className="opportunity-detail">{opp.detail}</div>
            </div>
          ))}
        </div>
      )}

      {content.friction_signals?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
            Friction Signals
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {content.friction_signals.map((fs, i) => (
              <span key={i} className="theme-chip" style={{ color: 'var(--amber)',
                borderColor: 'rgba(245,166,35,0.2)', background: 'rgba(245,166,35,0.06)' }}>
                ⚠ {fs}
              </span>
            ))}
          </div>
        </div>
      )}

      {content.recommended_action && (
        <div className="action-strip">
          <span className="action-strip-label">Next Step</span>
          <span className="action-strip-text">{content.recommended_action}</span>
        </div>
      )}
    </Card>
  )
}
