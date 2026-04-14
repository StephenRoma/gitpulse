import { useState, useEffect } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from '../api'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr + (dateStr.endsWith('Z') ? '' : 'Z')).getTime()
  const d = Math.floor(diff / 86400000)
  if (d < 1) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

function formatDateShort(dateStr) {
  if (!dateStr) return '—'
  try { return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }
  catch { return dateStr }
}

function formatMoney(n) {
  if (!n || n === 0) return 'TBD'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n}`
}

function SourceBadge({ source }) {
  const map = {
    google_news: { label: 'NEWS', fg: '#0369A1', bg: '#E0F2FE', bd: '#BAE6FD' },
    sam_gov:     { label: 'SAM.GOV', fg: '#166534', bg: '#F0FDF4', bd: '#BBF7D0' },
    manual:      { label: 'MANUAL', fg: '#7C3AED', bg: '#F5F3FF', bd: '#DDD6FE' },
  }
  const s = map[source] || map.manual
  return (
    <span style={{ fontSize: 8, fontFamily: 'var(--mono)', fontWeight: 700, padding: '1px 5px',
      borderRadius: 3, color: s.fg, background: s.bg, border: `1px solid ${s.bd}`, letterSpacing: '0.06em' }}>
      {s.label}
    </span>
  )
}

function DraftModal({ rfp, accounts, onClose }) {
  const [vendorName, setVendorName] = useState('')
  const [vendorDesc, setVendorDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [draft, setDraft] = useState(null)

  async function generate() {
    if (!vendorName.trim() || !vendorDesc.trim()) return
    setLoading(true)
    try {
      const res = await api.draftRFPProposal(rfp.id, vendorName.trim(), vendorDesc.trim())
      setDraft(res.draft)
    } catch (e) { alert(`Failed: ${e.message}`) }
    finally { setLoading(false) }
  }

  function copyDraft() {
    if (draft) navigator.clipboard.writeText(draft)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 2000, background: 'rgba(26,33,88,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, width: '100%', maxWidth: 680,
        maxHeight: '90vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
        padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 4 }}>AI PROPOSAL WRITER</div>
            <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 17, color: 'var(--navy)', lineHeight: 1.3 }}>{rfp.title}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--mono)' }}>{rfp.agency}</div>
          </div>
          <button onClick={onClose} style={{ border: 'none', background: 'transparent', fontSize: 20, color: 'var(--text-faint)', cursor: 'pointer' }}>✕</button>
        </div>

        {!draft ? (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>YOUR COMPANY NAME</label>
              <input value={vendorName} onChange={e => setVendorName(e.target.value)}
                placeholder="e.g. Acme EdTech Inc."
                style={{ padding: '8px 12px', borderRadius: 7, border: '1px solid var(--border)', fontFamily: 'var(--mono)', fontSize: 12 }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>WHAT YOUR PRODUCT DOES</label>
              <textarea value={vendorDesc} onChange={e => setVendorDesc(e.target.value)}
                rows={4} placeholder="Describe your platform, what problem it solves, key features..."
                style={{ padding: '8px 12px', borderRadius: 7, border: '1px solid var(--border)', fontFamily: 'var(--mono)', fontSize: 12, resize: 'vertical' }} />
            </div>
            <button onClick={generate} disabled={loading || !vendorName.trim() || !vendorDesc.trim()}
              style={{
                padding: '10px 20px', borderRadius: 8, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
                background: 'var(--magenta)', color: '#fff', fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13,
                opacity: loading ? 0.6 : 1, display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start',
              }}>
              {loading && <Spinner size={12} />}
              {loading ? 'Drafting...' : '✦ Draft Proposal with AI'}
            </button>
          </>
        ) : (
          <>
            <div style={{ background: '#F8F9FF', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 18px' }}>
              <pre style={{ fontFamily: 'var(--mono)', fontSize: 11, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: 'var(--navy)', margin: 0 }}>{draft}</pre>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={copyDraft} style={{
                padding: '8px 18px', borderRadius: 7, border: 'none', cursor: 'pointer',
                background: 'var(--navy)', color: '#fff', fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 700,
              }}>Copy Draft</button>
              <button onClick={() => setDraft(null)} style={{
                padding: '8px 18px', borderRadius: 7, border: '1px solid var(--border)', cursor: 'pointer',
                background: 'transparent', color: 'var(--text-secondary)', fontFamily: 'var(--mono)', fontSize: 11,
              }}>Regenerate</button>
              <button onClick={onClose} style={{
                padding: '8px 18px', borderRadius: 7, border: '1px solid var(--border)', cursor: 'pointer',
                background: 'transparent', color: 'var(--text-secondary)', fontFamily: 'var(--mono)', fontSize: 11,
              }}>Close</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function RFPRow({ rfp, onDraft, onDelete }) {
  const isDue = rfp.due_date && new Date(rfp.due_date) < new Date()
  const dueSoon = rfp.due_date && !isDue &&
    (new Date(rfp.due_date) - Date.now()) < 14 * 86400000

  return (
    <div style={{
      background: '#fff', border: `1px solid ${isDue ? '#FECDD3' : 'var(--border)'}`,
      borderRadius: 9, padding: '14px 18px', display: 'flex', alignItems: 'flex-start',
      gap: 16, opacity: isDue ? 0.65 : 1,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <SourceBadge source={rfp.source} />
          {isDue && <span style={{ fontSize: 8, fontFamily: 'var(--mono)', fontWeight: 700, padding: '1px 5px', borderRadius: 3, color: '#B91C1C', background: '#FEF2F2', border: '1px solid #FECACA' }}>CLOSED</span>}
          {dueSoon && <span style={{ fontSize: 8, fontFamily: 'var(--mono)', fontWeight: 700, padding: '1px 5px', borderRadius: 3, color: '#D97706', background: '#FFFBEB', border: '1px solid #FDE68A' }}>DUE SOON</span>}
        </div>
        <a href={rfp.url} target="_blank" rel="noopener noreferrer"
          style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 13, color: 'var(--navy)', textDecoration: 'none', lineHeight: 1.4, display: 'block', marginBottom: 3 }}>
          {rfp.title}
        </a>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginBottom: 6 }}>
          {rfp.agency}
          {rfp.account_name && <span style={{ color: 'var(--text-faint)' }}> · {rfp.account_name}</span>}
        </div>
        {rfp.description && (
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, fontFamily: 'var(--mono)', maxHeight: 44, overflow: 'hidden' }}>
            {rfp.description.slice(0, 180)}{rfp.description.length > 180 ? '...' : ''}
          </div>
        )}
        {rfp.proposal_draft && (
          <div style={{ marginTop: 6, fontSize: 9, fontFamily: 'var(--mono)', color: '#166534', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 4, padding: '2px 7px', display: 'inline-block' }}>
            ✓ Draft saved
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
        <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-faint)', textAlign: 'right' }}>
          {rfp.posted_date && <div>Posted {formatDateShort(rfp.posted_date)}</div>}
          {rfp.due_date && <div style={{ color: dueSoon ? '#D97706' : isDue ? '#B91C1C' : 'inherit' }}>Due {formatDateShort(rfp.due_date)}</div>}
          {rfp.estimated_value > 0 && <div style={{ color: '#166534', fontWeight: 700 }}>{formatMoney(rfp.estimated_value)}</div>}
        </div>
        <button onClick={() => onDraft(rfp)} style={{
          marginTop: 4, padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
          background: 'var(--magenta)', color: '#fff', fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
        }}>✦ Draft</button>
        <button onClick={() => onDelete(rfp.id)} style={{
          padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)', cursor: 'pointer',
          background: 'transparent', color: 'var(--text-faint)', fontFamily: 'var(--mono)', fontSize: 9,
        }}>Remove</button>
      </div>
    </div>
  )
}

export default function RFPPage({ accounts = [] }) {
  const [rfps, setRFPs] = useState([])
  const [loading, setLoading] = useState(true)
  const [scanningId, setScanningId] = useState(null)
  const [filterAccount, setFilterAccount] = useState(null)
  const [draftRFP, setDraftRFP] = useState(null)
  const [filterStatus, setFilterStatus] = useState('open') // 'all' | 'open' | 'draft'

  useEffect(() => {
    load()
  }, [])

  async function load() {
    setLoading(true)
    try { setRFPs(await api.getRFPs()) }
    catch { setRFPs([]) }
    finally { setLoading(false) }
  }

  async function scanAccount(accountId) {
    setScanningId(accountId)
    try {
      await api.scanRFPs(accountId)
      // Poll for new results
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const fresh = await api.getRFPs(accountId)
        if (fresh.length > rfps.filter(r => r.account_id === accountId).length) {
          setRFPs(await api.getRFPs())
          break
        }
      }
      setRFPs(await api.getRFPs())
    } catch (e) { alert(`Scan failed: ${e.message}`) }
    finally { setScanningId(null) }
  }

  async function deleteRFP(id) {
    await api.deleteRFP(id)
    setRFPs(prev => prev.filter(r => r.id !== id))
  }

  let displayed = [...rfps]
  if (filterAccount) displayed = displayed.filter(r => r.account_id === filterAccount)
  if (filterStatus === 'open') displayed = displayed.filter(r => !r.due_date || new Date(r.due_date) >= new Date())
  if (filterStatus === 'draft') displayed = displayed.filter(r => r.proposal_draft)

  const openCount  = rfps.filter(r => !r.due_date || new Date(r.due_date) >= new Date()).length
  const draftCount = rfps.filter(r => r.proposal_draft).length

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', background: 'var(--bg)' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.12em', marginBottom: 6 }}>PROCUREMENT INTELLIGENCE</div>
        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 22, color: 'var(--navy)', margin: 0 }}>AI RFP Finder & Proposal Writer</h1>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: 6 }}>
          Find RFPs matching your district accounts. Use AI to draft winning proposals in seconds.
        </p>
      </div>

      {/* Stats + Scan row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { label: 'TOTAL RFPs', value: rfps.length },
          { label: 'OPEN', value: openCount },
          { label: 'DRAFTS SAVED', value: draftCount },
        ].map(m => (
          <div key={m.label} style={{ padding: '10px 18px', borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--border)', minWidth: 100 }}>
            <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 3 }}>{m.label}</div>
            <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--display)', color: 'var(--navy)' }}>{m.value}</div>
          </div>
        ))}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {accounts.map(acct => (
            <button key={acct.id} onClick={() => scanAccount(acct.id)} disabled={scanningId === acct.id}
              style={{
                padding: '7px 14px', borderRadius: 8, border: '1px solid var(--border)',
                background: scanningId === acct.id ? 'var(--bg)' : 'var(--navy)', color: scanningId === acct.id ? 'var(--text-muted)' : '#fff',
                fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700, cursor: scanningId === acct.id ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
              {scanningId === acct.id && <Spinner size={10} />}
              Scan {acct.name}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 4 }}>STATUS</span>
        {[['all','All'],['open','Open'],['draft','Has Draft']].map(([k, l]) => (
          <button key={k} onClick={() => setFilterStatus(k)} style={{
            padding: '3px 10px', borderRadius: 5, border: `1px solid ${filterStatus === k ? 'var(--navy)' : 'var(--border)'}`,
            background: filterStatus === k ? 'var(--navy)' : 'transparent',
            color: filterStatus === k ? '#fff' : 'var(--text-secondary)',
            fontFamily: 'var(--mono)', fontSize: 10, cursor: 'pointer', fontWeight: filterStatus === k ? 700 : 400,
          }}>{l}</button>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', marginRight: 4 }}>ACCOUNT</span>
        <select value={filterAccount || ''} onChange={e => setFilterAccount(e.target.value ? parseInt(e.target.value) : null)}
          style={{ fontSize: 10, fontFamily: 'var(--mono)', padding: '3px 8px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface)' }}>
          <option value="">All Accounts</option>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </div>

      {/* RFP List */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
      ) : displayed.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📋</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)', marginBottom: 6 }}>No RFPs found yet</div>
          <div style={{ fontSize: 12 }}>Click "Scan [Account]" above to search for procurement opportunities.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {displayed.map(rfp => (
            <RFPRow key={rfp.id} rfp={rfp} onDraft={setDraftRFP} onDelete={deleteRFP} />
          ))}
        </div>
      )}

      {draftRFP && (
        <DraftModal rfp={draftRFP} accounts={accounts} onClose={() => setDraftRFP(null)} />
      )}
    </div>
  )
}
