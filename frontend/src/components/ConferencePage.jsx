import { useState, useEffect } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from '../api'

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try { return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }
  catch { return dateStr }
}

function daysLabel(days) {
  if (days === null || days === undefined) return ''
  if (days < 0) return 'Past'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days <= 7)  return `${days}d`
  if (days <= 30) return `${Math.round(days / 7)}w`
  return `${Math.round(days / 30)}mo`
}

function daysColor(days) {
  if (days === null || days === undefined) return 'var(--text-faint)'
  if (days < 0)   return '#B91C1C'
  if (days <= 30) return '#D97706'
  return '#166534'
}

function TagChip({ tag }) {
  const colors = {
    edtech: '#7C3AED', curriculum: '#0369A1', devices: '#059669',
    cybersecurity: '#C8005A', ai: '#1A6B9A', policy: '#374060',
    cto: '#D97706', it_leaders: '#D97706', innovation: '#7C3AED',
    startups: '#C8005A', investment: '#166534', texas: '#B45309',
    california: '#2563EB', florida: '#059669', pacific_northwest: '#2D6A4F',
    nyc: '#374060', professional_dev: '#0891B2',
  }
  const color = colors[tag] || '#6B7280'
  return (
    <span style={{
      fontSize: 8, fontFamily: 'var(--mono)', padding: '1px 6px', borderRadius: 4,
      background: color + '18', color, border: `1px solid ${color}44`,
      fontWeight: 600, letterSpacing: '0.04em',
    }}>{tag.replace(/_/g, ' ').toUpperCase()}</span>
  )
}

function ConferenceCard({ conf, showRelevance }) {
  const days = conf.days_until ?? null
  const isPast = days !== null && days < 0

  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)', borderRadius: 10,
      padding: '16px 20px', opacity: isPast ? 0.6 : 1, position: 'relative',
      transition: 'box-shadow 0.15s',
    }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.07)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      {/* Relevance badge */}
      {showRelevance && conf.relevance_score !== undefined && (
        <div style={{
          position: 'absolute', top: 12, right: 14,
          fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, padding: '2px 7px',
          borderRadius: 5,
          color: conf.relevance_score >= 70 ? '#C8005A' : conf.relevance_score >= 50 ? '#D97706' : '#6B7280',
          background: conf.relevance_score >= 70 ? '#FFF0F5' : conf.relevance_score >= 50 ? '#FFFBEB' : '#F9FAFB',
          border: `1px solid ${conf.relevance_score >= 70 ? '#FBCFE8' : conf.relevance_score >= 50 ? '#FDE68A' : '#E5E7EB'}`,
        }}>
          {conf.relevance_score >= 70 ? '★ ' : ''}{conf.relevance_score}% match
        </div>
      )}

      {/* Days countdown */}
      {days !== null && !isPast && (
        <div style={{
          fontSize: 9, fontFamily: 'var(--mono)', marginBottom: 8, color: daysColor(days), fontWeight: 700,
        }}>
          ⏱ {daysLabel(days)} away
        </div>
      )}
      {isPast && (
        <div style={{ fontSize: 9, fontFamily: 'var(--mono)', marginBottom: 8, color: '#B91C1C', fontWeight: 700 }}>PAST</div>
      )}

      <a href={conf.url} target="_blank" rel="noopener noreferrer"
        style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 14, color: 'var(--navy)', textDecoration: 'none', lineHeight: 1.3, display: 'block', marginBottom: 6, paddingRight: showRelevance ? 90 : 0 }}>
        {conf.name}
      </a>

      <div style={{ display: 'flex', gap: 14, fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)', marginBottom: 8 }}>
        <span>📅 {formatDate(conf.start_date)}{conf.end_date && conf.end_date !== conf.start_date ? ` – ${formatDate(conf.end_date)}` : ''}</span>
        <span>📍 {conf.city || conf.location}</span>
        {conf.attendee_count > 0 && <span>👥 {conf.attendee_count.toLocaleString()}</span>}
        {conf.is_virtual ? <span style={{ color: '#7C3AED' }}>Virtual</span> : null}
      </div>

      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: conf.notes ? 8 : 0 }}>
        {(conf.theme_tags || []).map(t => <TagChip key={t} tag={t} />)}
      </div>

      {conf.notes && (
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, fontFamily: 'var(--mono)', borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 4 }}>
          {conf.notes}
        </div>
      )}
    </div>
  )
}

export default function ConferencePage({ accounts = [] }) {
  const [conferences, setConferences] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedAccount, setSelectedAccount] = useState(null)
  const [showPast, setShowPast] = useState(false)
  const [filterTag, setFilterTag] = useState(null)

  useEffect(() => {
    loadConferences()
  }, [])

  useEffect(() => {
    if (selectedAccount) {
      loadForAccount(selectedAccount)
    } else {
      loadConferences()
    }
  }, [selectedAccount])

  async function loadConferences() {
    setLoading(true)
    try { setConferences(await api.getConferences()) }
    catch { setConferences([]) }
    finally { setLoading(false) }
  }

  async function loadForAccount(accountId) {
    setLoading(true)
    try { setConferences(await api.getConferencesForAccount(accountId)) }
    catch { setConferences([]) }
    finally { setLoading(false) }
  }

  // Collect all unique tags for filter strip
  const allTags = [...new Set((conferences || []).flatMap(c => c.theme_tags || []))]

  let displayed = [...conferences]
  if (!showPast) displayed = displayed.filter(c => c.days_until === null || c.days_until >= 0)
  if (filterTag) displayed = displayed.filter(c => (c.theme_tags || []).includes(filterTag))

  const upcomingCount = conferences.filter(c => c.days_until !== null && c.days_until >= 0).length
  const soonCount = conferences.filter(c => c.days_until !== null && c.days_until >= 0 && c.days_until <= 30).length

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', background: 'var(--bg)' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.12em', marginBottom: 6 }}>PIPELINE INTELLIGENCE</div>
        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 22, color: 'var(--navy)', margin: 0 }}>Conference Intelligence</h1>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: 6 }}>
          Discover the right EdTech events, match them to your accounts, and plan outreach around key conferences.
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          { label: 'UPCOMING', value: upcomingCount },
          { label: 'NEXT 30 DAYS', value: soonCount },
          { label: 'TOTAL TRACKED', value: conferences.length },
        ].map(m => (
          <div key={m.label} style={{ padding: '10px 18px', borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--border)', minWidth: 100 }}>
            <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 3 }}>{m.label}</div>
            <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--display)', color: 'var(--navy)' }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Account selector for relevance scoring */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>MATCH TO ACCOUNT</span>
        <select value={selectedAccount || ''} onChange={e => setSelectedAccount(e.target.value ? parseInt(e.target.value) : null)}
          style={{ fontSize: 11, fontFamily: 'var(--mono)', padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--navy)' }}>
          <option value="">— Show all —</option>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={showPast} onChange={e => setShowPast(e.target.checked)} />
          Show past
        </label>
      </div>

      {/* Tag filters */}
      {allTags.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
          <button onClick={() => setFilterTag(null)} style={{
            padding: '2px 10px', borderRadius: 5, border: `1px solid ${!filterTag ? 'var(--navy)' : 'var(--border)'}`,
            background: !filterTag ? 'var(--navy)' : 'transparent', color: !filterTag ? '#fff' : 'var(--text-secondary)',
            fontFamily: 'var(--mono)', fontSize: 9, cursor: 'pointer', fontWeight: !filterTag ? 700 : 400,
          }}>ALL</button>
          {allTags.slice(0, 14).map(t => (
            <button key={t} onClick={() => setFilterTag(filterTag === t ? null : t)} style={{
              padding: '2px 10px', borderRadius: 5, border: `1px solid ${filterTag === t ? 'var(--navy)' : 'var(--border)'}`,
              background: filterTag === t ? 'var(--navy)' : 'transparent', color: filterTag === t ? '#fff' : 'var(--text-secondary)',
              fontFamily: 'var(--mono)', fontSize: 9, cursor: 'pointer', fontWeight: filterTag === t ? 700 : 400,
              textTransform: 'uppercase',
            }}>{t.replace(/_/g, ' ')}</button>
          ))}
        </div>
      )}

      {/* Conference grid */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
      ) : displayed.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>🎪</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)', marginBottom: 6 }}>No conferences found</div>
          <div style={{ fontSize: 12 }}>Try showing past events or clearing filters.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 14 }}>
          {displayed.map(conf => (
            <ConferenceCard key={conf.id} conf={conf} showRelevance={!!selectedAccount} />
          ))}
        </div>
      )}

    </div>
  )
}
