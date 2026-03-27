import { Button, Intent, Spinner, ProgressBar, Tooltip } from '@blueprintjs/core'
import { useState } from 'react'
import { api } from '../api'

function ScorePanel({ score }) {
  return (
    <div className="score-ring-wrap">
      <div>
        <div className="score-number">{score}</div>
        <div className="score-label">Signal Score</div>
      </div>
      <div style={{ flex: 1 }}>
        <ProgressBar
          value={score / 100}
          intent={score >= 60 ? Intent.SUCCESS : score >= 25 ? Intent.WARNING : Intent.NONE}
          stripes={false}
          animate={false}
          style={{ height: 6, borderRadius: 4 }}
        />
        <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
          {score >= 60 ? 'High intent · Prioritize outreach'
            : score >= 25 ? 'Moderate signals · Continue monitoring'
            : 'Low signals · Expand engineer list'}
        </div>
      </div>
    </div>
  )
}

function EngineerList({ engineers, accountId, onRefresh }) {
  const [adding, setAdding] = useState(false)
  const [newHandle, setNewHandle] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleAdd() {
    if (!newHandle.trim()) return
    setLoading(true)
    try {
      await api.addEngineer(accountId, newHandle.trim())
      setNewHandle('')
      setAdding(false)
      onRefresh()
    } finally {
      setLoading(false)
    }
  }

  async function handleRemove(engineerId) {
    await api.removeEngineer(engineerId)
    onRefresh()
  }

  return (
    <div style={{ marginBottom: 24 }}>
      <div className="right-section-label">Engineers Tracked</div>

      {engineers.map(eng => (
        <div key={eng.id} className="engineer-row">
          <div className="engineer-avatar">
            {eng.avatar_url
              ? <img src={eng.avatar_url} alt={eng.github_username} />
              : eng.github_username.slice(0, 2).toUpperCase()
            }
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="engineer-name">{eng.display_name || eng.github_username}</div>
            <div className="engineer-handle">@{eng.github_username}</div>
          </div>
          <Button
            icon="trash" minimal small
            style={{ color: 'var(--text-muted)' }}
            onClick={() => handleRemove(eng.id)}
          />
        </div>
      ))}

      {adding ? (
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <input
            className="bp5-input bp5-small"
            placeholder="github-username"
            value={newHandle}
            onChange={e => setNewHandle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            style={{ flex: 1 }}
            autoFocus
          />
          <Button icon="tick" minimal small loading={loading} onClick={handleAdd} />
          <Button icon="cross" minimal small onClick={() => { setAdding(false); setNewHandle('') }} />
        </div>
      ) : (
        <Button
          icon="plus" text="Add Engineer" minimal small
          style={{ color: 'var(--text-muted)', marginTop: 8 }}
          onClick={() => setAdding(true)}
        />
      )}
    </div>
  )
}

function StackPanel({ signals }) {
  // Tally languages and topics
  const langCount = {}
  const topicCount = {}

  for (const s of signals) {
    if (s.repo_language) {
      langCount[s.repo_language] = (langCount[s.repo_language] || 0) + 1
    }
    for (const t of (s.repo_topics || [])) {
      topicCount[t] = (topicCount[t] || 0) + 1
    }
  }

  const langs = Object.entries(langCount).sort((a, b) => b[1] - a[1]).slice(0, 6)
  const topics = Object.entries(topicCount).sort((a, b) => b[1] - a[1]).slice(0, 8)

  return (
    <div style={{ marginBottom: 24 }}>
      <div className="right-section-label">Stack Signals</div>

      {langs.length === 0 && topics.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          No stack data yet — run a sync.
        </div>
      )}

      {langs.map(([lang, count]) => (
        <div key={lang} className="stack-chip">
          <span className="stack-chip-name">{lang}</span>
          <span className="stack-chip-count">{count}×</span>
        </div>
      ))}

      {topics.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {topics.map(([topic, count]) => (
            <span key={topic} className="topic-tag" style={{ fontSize: 11 }}>
              {topic} ·{count}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function RightPanel({ account, engineers, signals, onRefresh, syncStatus, onSync }) {
  return (
    <div className="gp-right bp5-dark">
      <ScorePanel score={account?.signal_score || 0} />

      <div style={{ marginBottom: 16 }}>
        <Button
          icon="refresh"
          text={syncStatus?.status === 'syncing' || syncStatus?.status === 'briefing'
            ? 'Syncing…' : 'Sync Account'}
          intent={Intent.PRIMARY}
          fill
          loading={syncStatus?.status === 'syncing' || syncStatus?.status === 'briefing'}
          onClick={onSync}
        />
        {syncStatus?.detail && (
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-muted)',
            marginTop: 6, textAlign: 'center' }}>
            {syncStatus.detail}
          </div>
        )}
      </div>

      <EngineerList
        engineers={engineers}
        accountId={account?.id}
        onRefresh={onRefresh}
      />

      <StackPanel signals={signals} />
    </div>
  )
}
