import { useState, useRef, useEffect } from 'react'
import { Spinner } from '@blueprintjs/core'

const SIGNAL_ICONS   = { board_minutes_item: '📋', essa_profile: '📊', state_initiative: '🏛', job_posting: '💼', news_mention: '📰', press_release: '📣', star: '★', fork: '⑂', new_repo: '◈', push: '↑', issue_comment: '💬', release: '🏷', org_issue: '⚠', hn_mention: '◎', sec_filing: '🏛', reddit_buzz: '⬆' }
const SIGNAL_ACTIONS = { board_minutes_item: 'board minutes item', essa_profile: 'ESSA profile updated', state_initiative: 'state initiative', job_posting: 'job posting', news_mention: 'in the news', press_release: 'press release', star: 'starred', fork: 'forked', new_repo: 'created repo', push: 'pushed to', issue_comment: 'commented on issue in', release: 'published release', org_issue: 'open issue on', hn_mention: 'mentioned on HN', sec_filing: 'filed 8-K with SEC', reddit_buzz: 'discussed on Reddit' }
const TYPE_LABELS    = { board_minutes_item: 'Board Minutes', essa_profile: 'ESSA Profile', state_initiative: 'State Initiative', job_posting: 'Job Posting', news_mention: 'News', press_release: 'Press Release' }

function sigScore(signal) {
  try { return JSON.parse(signal.raw_data || '{}').sig_score || 0 } catch { return 0 }
}

function sigHeat(signal) {
  const score = sigScore(signal)
  return score >= 6 ? 'hot' : score >= 3 ? 'warm' : 'cool'
}

function sigCertainty(signal) {
  try { return JSON.parse(signal.raw_data || '{}').certainty || 'evaluating' } catch { return 'evaluating' }
}

const CERTAINTY_OPTS = [
  { key: null,          label: 'All' },
  { key: 'confirmed',   label: 'Confirmed',  fg: '#166534', bg: '#F0FDF4', bd: '#BBF7D0' },
  { key: 'active',      label: 'Active',     fg: '#0369A1', bg: '#EFF6FF', bd: '#BFDBFE' },
  { key: 'evaluating',  label: 'Evaluating', fg: '#92400E', bg: '#FFFBEB', bd: '#FDE68A' },
]
const CERTAINTY_MAP = Object.fromEntries(CERTAINTY_OPTS.filter(o => o.key).map(o => [o.key, o]))

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

const RELEVANCE_OPTS = [
  { label: 'All',    min: 0,  desc: 'all signals' },
  { label: '3+',     min: 3,  desc: 'relevant' },
  { label: '6+',     min: 6,  desc: 'high signal only' },
]

const THEMES = [
  { key: 'modernization',   label: 'Modernization',         color: '#7C3AED' },
  { key: 'cloud_migration', label: 'Cloud Migration',        color: '#0369A1' },
  { key: 'ai_adoption',     label: 'AI / ML Adoption',       color: '#0891B2' },
  { key: 'security',        label: 'Security & Compliance',  color: '#C8005A' },
  { key: 'platform_eng',    label: 'Platform Engineering',   color: '#1A2158' },
  { key: 'vendor_eval',     label: 'Vendor Evaluation',      color: '#D97706' },
  { key: 'tech_debt',       label: 'Tech Debt',              color: '#B85042' },
  { key: 'performance',     label: 'Performance',            color: '#2D6A4F' },
  { key: 'devex',           label: 'Developer Experience',   color: '#374060' },
]
const THEME_MAP = Object.fromEntries(THEMES.map(t => [t.key, t]))

function TagPopover({ signalId, activeTags = [], onTag, onUntag, onClose }) {
  const ref = useRef(null)
  useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) onClose() }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])
  return (
    <div ref={ref} style={{
      position: 'absolute', zIndex: 200, right: 0, top: '100%', marginTop: 4,
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
      padding: '8px', display: 'flex', flexWrap: 'wrap', gap: 5, width: 240,
    }}>
      <div style={{ width: '100%', fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)',
        letterSpacing: '0.1em', marginBottom: 2 }}>TAG THEME</div>
      {THEMES.map(t => {
        const active = activeTags.includes(t.key)
        return (
          <span key={t.key}
            onClick={() => active ? onUntag(signalId, t.key) : onTag(signalId, t.key)}
            style={{
              cursor: 'pointer', userSelect: 'none',
              padding: '3px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'var(--mono)',
              border: `1px solid ${t.color}`,
              background: active ? t.color : 'transparent',
              color: active ? '#fff' : t.color,
              fontWeight: active ? 700 : 400,
              transition: 'all 0.1s',
            }}>{t.label}</span>
        )
      })}
    </div>
  )
}

const BOARD_TYPES = new Set(['board_minutes_item','essa_profile','state_initiative'])
const NEWS_TYPES  = new Set(['news_mention','press_release','job_posting'])

const NEWS_CAT_COLORS = {
  risk:      { fg: '#991B1B', bg: '#FEF2F2', bd: '#FECACA' },
  financial: { fg: '#065F46', bg: '#ECFDF5', bd: '#6EE7B7' },
  product:   { fg: '#1E40AF', bg: '#EFF6FF', bd: '#BFDBFE' },
  general:   { fg: '#6B7280', bg: '#F9FAFB', bd: '#E5E7EB' },
}

export default function SignalFeed({ signals, loading, engineers = [], signalTags = {}, onTagSignal, onUntagSignal }) {
  const [activeHeat,      setActiveHeat]      = useState(null)
  const [activeType,      setActiveType]      = useState(null)
  const [activeEngineer,  setActiveEngineer]  = useState('')
  const [minScore,        setMinScore]        = useState(0)
  const [activeCertainty, setActiveCertainty] = useState(null)
  const [openTagId,       setOpenTagId]       = useState(null)
  const [sourceFilter,    setSourceFilter]    = useState('all') // 'all' | 'board' | 'news'

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
        No signals yet. Run a Scan to collect district signals.
      </div>
    )
  }

  const filtered = signals.filter(s =>
    (!activeHeat      || sigHeat(s) === activeHeat) &&
    (!activeType      || s.signal_type === activeType) &&
    (!activeEngineer  || s.engineer_username === activeEngineer) &&
    (!activeCertainty || sigCertainty(s) === activeCertainty) &&
    (sigScore(s) >= minScore) &&
    (sourceFilter === 'all' ||
     (sourceFilter === 'board' && BOARD_TYPES.has(s.signal_type)) ||
     (sourceFilter === 'news'  && NEWS_TYPES.has(s.signal_type)))
  )
  const filtersActive = activeHeat || activeType || activeEngineer || minScore > 0 || activeCertainty || sourceFilter !== 'all'

  function toggleHeat(h)      { setActiveHeat(prev => prev === h ? null : h) }
  function toggleType(t)      { setActiveType(prev => prev === t ? null : t) }
  function toggleCertainty(c) { setActiveCertainty(prev => prev === c ? null : c) }
  function clearFilters()     { setActiveHeat(null); setActiveType(null); setActiveEngineer(''); setMinScore(0); setActiveCertainty(null); setSourceFilter('all') }

  const chipBase = { cursor: 'pointer', userSelect: 'none', border: '1px solid', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'var(--mono)', transition: 'all 0.15s' }

  return (
    <div>
      {/* Filter bar */}
      <div style={{ padding: '10px 0 8px', display: 'flex', flexDirection: 'column', gap: 7 }}>

        {/* Row 0: Source toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>SOURCE</span>
          {[['all','All'],['board','Board & Gov'],['news','News & Jobs']].map(([k,l]) => (
            <span key={k} onClick={() => setSourceFilter(k)} style={{
              ...chipBase,
              color: sourceFilter === k ? 'var(--navy)' : 'var(--text-secondary)',
              background: sourceFilter === k ? 'var(--bg)' : 'transparent',
              borderColor: sourceFilter === k ? 'var(--navy)' : 'var(--border)',
              fontWeight: sourceFilter === k ? 700 : 400,
            }}>{l}</span>
          ))}
        </div>

        {/* Row 1: Heat filters + count */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>HEAT</span>
          {['hot', 'warm', 'cool'].map(h => (
            <span key={h} onClick={() => toggleHeat(h)} style={{
              ...chipBase,
              color: heatFg(h),
              background: activeHeat === h ? heatBg(h) : 'transparent',
              borderColor: activeHeat === h ? heatBd(h) : 'var(--border)',
              fontWeight: activeHeat === h ? 700 : 400,
            }}>{h.toUpperCase()}</span>
          ))}
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
            {filtersActive ? `${filtered.length} of ${signals.length}` : `${signals.length} signals`}
          </span>
        </div>

        {/* Row 2: Type chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>TYPE</span>
          {Object.entries(TYPE_LABELS).map(([t, label]) => (
            <span key={t} onClick={() => toggleType(t)} style={{
              ...chipBase,
              color: activeType === t ? 'var(--navy)' : 'var(--text-secondary)',
              background: activeType === t ? 'var(--bg)' : 'transparent',
              borderColor: activeType === t ? 'var(--navy)' : 'var(--border)',
              fontWeight: activeType === t ? 700 : 400,
            }}>{SIGNAL_ICONS[t]} {label}</span>
          ))}
        </div>

        {/* Row 3: Relevance filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>RELEVANCE</span>
          {RELEVANCE_OPTS.map(opt => (
            <span key={opt.min} onClick={() => setMinScore(opt.min)} title={opt.desc} style={{
              ...chipBase,
              color: minScore === opt.min ? 'var(--navy)' : 'var(--text-secondary)',
              background: minScore === opt.min ? 'var(--bg)' : 'transparent',
              borderColor: minScore === opt.min ? 'var(--navy)' : 'var(--border)',
              fontWeight: minScore === opt.min ? 700 : 400,
            }}>{opt.label}</span>
          ))}
        </div>

        {/* Row 4: Certainty filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>CERTAINTY</span>
          {CERTAINTY_OPTS.map(opt => {
            const active = activeCertainty === opt.key
            const fg = opt.fg || 'var(--text-secondary)'
            const bg = opt.bg || 'var(--bg)'
            const bd = opt.bd || 'var(--border)'
            return (
              <span key={String(opt.key)} onClick={() => toggleCertainty(opt.key)} style={{
                ...chipBase,
                color: active ? fg : 'var(--text-secondary)',
                background: active ? bg : 'transparent',
                borderColor: active ? bd : 'var(--border)',
                fontWeight: active ? 700 : 400,
              }}>{opt.label}</span>
            )
          })}
        </div>

        {/* Row 5: Engineer dropdown + clear */}
        {engineers.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 2 }}>CONTACT</span>
            <select value={activeEngineer} onChange={e => setActiveEngineer(e.target.value)} style={{
              fontSize: 10, fontFamily: 'var(--mono)', border: '1px solid var(--border)',
              borderRadius: 4, padding: '2px 6px', background: 'var(--surface)', color: 'var(--navy)', cursor: 'pointer',
            }}>
              <option value="">All Contacts</option>
              {engineers.map(eng => (
                <option key={eng.id} value={eng.name || eng.id}>{eng.name || eng.role || 'Contact'}</option>
              ))}
            </select>
            {filtersActive && (
              <button onClick={clearFilters} style={{
                fontSize: 10, fontFamily: 'var(--mono)', border: '1px solid var(--border)',
                borderRadius: 4, padding: '2px 8px', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer',
              }}>Clear</button>
            )}
          </div>
        )}
      </div>

      {filtered.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32, fontSize: 13, fontFamily: 'var(--mono)' }}>
          No signals match the current filters.
        </div>
      ) : (
        filtered.map(s => {
          const heat      = sigHeat(s)
          const certainty = sigCertainty(s)
          const certOpt   = CERTAINTY_MAP[certainty] || CERTAINTY_MAP['evaluating']
          const icon   = SIGNAL_ICONS[s.signal_type]   || '\u00B7'
          const action = SIGNAL_ACTIONS[s.signal_type] || s.signal_type
          let raw = {}
          try { raw = JSON.parse(s.raw_data || '{}') } catch {}

          // Build the detail line depending on signal type
          let detail = null
          if (s.signal_type === 'issue_comment') {
            const labels = (raw.labels || []).slice(0, 3)
            detail = (
              <>
                <a href={s.repo_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', fontSize: 11 }}>{s.repo_name}</a>
                {raw.issue_title && <span style={{ color: 'var(--text-secondary)', marginLeft: 6, fontSize: 11 }}>"{raw.issue_title.slice(0,60)}"</span>}
                {labels.map(l => <span key={l} style={{ marginLeft: 4, fontSize: 9, padding: '1px 5px', borderRadius: 3, background: '#FEF3C7', border: '1px solid #FDE68A', color: '#92400E' }}>{l}</span>)}
              </>
            )
          } else if (s.signal_type === 'release') {
            detail = (
              <>
                <a href={s.repo_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', fontSize: 11 }}>{s.repo_name}</a>
                {raw.tag && <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#F0FDF4', border: '1px solid #BBF7D0', color: '#166534', fontFamily: 'var(--mono)' }}>{raw.tag}</span>}
                {raw.release_name && <span style={{ color: 'var(--text-secondary)', marginLeft: 6, fontSize: 11 }}>{raw.release_name.slice(0,50)}</span>}
                {raw.prerelease && <span style={{ marginLeft: 4, fontSize: 9, padding: '1px 5px', borderRadius: 3, background: '#FFF7ED', border: '1px solid #FED7AA', color: '#9A3412' }}>PRE</span>}
              </>
            )
          } else if (s.signal_type === 'org_issue') {
            const labels = (raw.labels || []).slice(0, 3)
            detail = (
              <>
                <a href={s.repo_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', fontSize: 11 }}>{s.repo_name}</a>
                {raw.issue_number && <span style={{ color: 'var(--text-faint)', marginLeft: 4, fontSize: 10 }}>#{raw.issue_number}</span>}
                {raw.issue_title && <span style={{ color: 'var(--text-secondary)', marginLeft: 6, fontSize: 11 }}>"{raw.issue_title.slice(0,60)}"</span>}
                {labels.map(l => <span key={l} style={{ marginLeft: 4, fontSize: 9, padding: '1px 5px', borderRadius: 3, background: '#FEF3C7', border: '1px solid #FDE68A', color: '#92400E' }}>{l}</span>)}
              </>
            )
          } else if (s.signal_type === 'hn_mention') {
            detail = (
              <>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{(s.repo_description || raw.text_preview || '').slice(0,80)}</span>
                {raw.points > 0 && <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#FFF7ED', border: '1px solid #FED7AA', color: '#C2410C' }}>{raw.points}pts</span>}
              </>
            )
          } else if (s.signal_type === 'news_mention' || s.signal_type === 'press_release') {
            const cat = raw.news_category || 'general'
            const catColors = NEWS_CAT_COLORS[cat] || NEWS_CAT_COLORS.general
            detail = (
              <>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{(raw.headline || s.repo_description || '').slice(0,100)}</span>
                <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 6px', borderRadius: 3,
                  background: catColors.bg, border: `1px solid ${catColors.bd}`, color: catColors.fg,
                  fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.04em' }}>{cat.toUpperCase()}</span>
                {raw.source && <span style={{ marginLeft: 4, fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>{raw.source}</span>}
              </>
            )
          } else if (s.signal_type === 'sec_filing') {
            detail = (
              <>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{raw.company || s.repo_description}</span>
                <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 6px', borderRadius: 3,
                  background: '#ECFDF5', border: '1px solid #6EE7B7', color: '#065F46',
                  fontFamily: 'var(--mono)', fontWeight: 700 }}>{raw.form_type || '8-K'}</span>
                {raw.filed_date && <span style={{ marginLeft: 4, fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>{raw.filed_date}</span>}
              </>
            )
          } else if (s.signal_type === 'reddit_buzz') {
            const cat = raw.news_category || 'general'
            const catColors = NEWS_CAT_COLORS[cat] || NEWS_CAT_COLORS.general
            detail = (
              <>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{(raw.headline || s.repo_description || '').slice(0,100)}</span>
                <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 6px', borderRadius: 3,
                  background: catColors.bg, border: `1px solid ${catColors.bd}`, color: catColors.fg,
                  fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.04em' }}>{cat.toUpperCase()}</span>
                {raw.subreddit && <span style={{ marginLeft: 4, fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>r/{raw.subreddit}</span>}
                {raw.num_comments > 0 && <span style={{ marginLeft: 4, fontSize: 9, padding: '1px 5px', borderRadius: 3, background: '#FFF7ED', border: '1px solid #FED7AA', color: '#C2410C' }}>{raw.num_comments} comments</span>}
              </>
            )
          } else {
            detail = (
              <>
                <a href={s.repo_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: '#1A6B9A', fontFamily: 'var(--mono)', fontSize: 11 }}>{s.repo_name}</a>
                {s.repo_language && (
                  <span style={{ marginLeft: 8, fontSize: 10, padding: '1px 6px', borderRadius: 4,
                    background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                    {s.repo_language}
                  </span>
                )}
              </>
            )
          }

          const tags = signalTags[s.id] || []
          const isTagged = tags.length > 0

          return (
            <div key={s.id} className="signal-row" style={isTagged ? { borderLeft: '3px solid #7C3AED', paddingLeft: 9 } : {}}>
              <div className="signal-icon-box" style={{
                color: heatFg(heat), background: heatBg(heat), borderColor: heatBd(heat),
              }}>{icon}</div>
              <div className="signal-user">@{s.engineer_username}</div>
              <div style={{ flex: 1, fontSize: 11, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
                <span style={{ color: 'var(--text-faint)', marginRight: 2 }}>{action}</span>
                {detail}
                {/* Tag pills */}
                {tags.map(tk => {
                  const theme = THEME_MAP[tk]
                  if (!theme) return null
                  return (
                    <span key={tk} style={{
                      marginLeft: 4, fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      background: theme.color, color: '#fff', fontFamily: 'var(--mono)',
                      fontWeight: 600, letterSpacing: '0.04em',
                    }}>{theme.label}</span>
                  )
                })}
              </div>
              <div className="signal-heat-badge" style={{
                fontSize: 8, padding: '2px 5px', borderRadius: 3, fontFamily: 'var(--mono)',
                fontWeight: 700, letterSpacing: '0.06em', whiteSpace: 'nowrap', flexShrink: 0,
                color: certOpt.fg, background: certOpt.bg, border: `1px solid ${certOpt.bd}`,
              }}>{certainty.toUpperCase()}</div>
              <div className="signal-heat-badge" style={{
                color: heatFg(heat), background: heatBg(heat), borderColor: heatBd(heat),
              }}>{heat.toUpperCase()}</div>
              <div className="signal-time" title={raw.pub_date ? `Published ${raw.pub_date} · Detected ${timeAgo(s.detected_at)}` : `Detected ${timeAgo(s.detected_at)}`}>
                {raw.pub_date
                  ? new Date(raw.pub_date + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
                  : timeAgo(s.detected_at)}
              </div>
              {/* Tag button */}
              {onTagSignal && (
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <button
                    onClick={() => setOpenTagId(prev => prev === s.id ? null : s.id)}
                    title="Tag signal theme"
                    style={{
                      background: isTagged ? '#7C3AED' : 'transparent',
                      border: `1px solid ${isTagged ? '#7C3AED' : 'var(--border)'}`,
                      borderRadius: 4, padding: '2px 5px', cursor: 'pointer',
                      fontSize: 10, color: isTagged ? '#fff' : 'var(--text-faint)',
                      lineHeight: 1,
                    }}
                  >&#127991;</button>
                  {openTagId === s.id && (
                    <TagPopover
                      signalId={s.id}
                      activeTags={tags}
                      onTag={onTagSignal}
                      onUntag={onUntagSignal}
                      onClose={() => setOpenTagId(null)}
                    />
                  )}
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}
