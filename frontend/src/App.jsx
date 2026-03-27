import { useEffect, useState, useCallback } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from './api'
import TopNav from './components/TopNav'
import AccountSidebar from './components/AccountSidebar'
import BriefingCard from './components/BriefingCard'
import SignalFeed from './components/SignalFeed'
import RightPanel from './components/RightPanel'
import AddAccountDialog from './components/AddAccountDialog'
import OutreachModal from './components/OutreachModal'

const PALETTE = [
  '#C8005A','#1A6B9A','#2D6A4F','#6D3A9C',
  '#B85042','#D97706','#0369A1','#374060'
]

function initials(name) {
  if (!name) return '??'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function sigHeat(signal) {
  try {
    const score = JSON.parse(signal.raw_data || '{}').sig_score || 0
    return score >= 6 ? 'hot' : score >= 3 ? 'warm' : 'cool'
  } catch (e) { return 'cool' }
}

function scoreFg(s)  { return s >= 85 ? '#C8005A' : s >= 60 ? '#D97706' : '#2563EB' }
function scoreBg(s)  { return s >= 85 ? '#FFF0F5' : s >= 60 ? '#FFFBEB' : '#EFF6FF' }
function scoreBd(s)  { return s >= 85 ? '#FBCFE8' : s >= 60 ? '#FDE68A' : '#BFDBFE' }
function scoreLbl(s) { return s >= 85 ? 'HOT'     : s >= 60 ? 'WARM'    : 'COOL'   }

function heatFg(h) { return h === 'hot' ? '#C8005A' : h === 'warm' ? '#D97706' : '#2563EB' }
function heatBg(h) { return h === 'hot' ? '#FFF0F5' : h === 'warm' ? '#FFFBEB' : '#EFF6FF' }
function heatBd(h) { return h === 'hot' ? '#FBCFE8' : h === 'warm' ? '#FDE68A' : '#BFDBFE' }

export default function App() {
  const [accounts, setAccounts]               = useState([])
  const [selectedId, setSelectedId]           = useState(null)
  const [signals, setSignals]                 = useState([])
  const [briefing, setBriefing]               = useState(null)
  const [engineers, setEngineers]             = useState([])
  const [syncing, setSyncing]                 = useState(false)
  const [briefingLoading, setBriefingLoading] = useState(false)
  const [addOpen, setAddOpen]                 = useState(false)
  const [outreachOpen, setOutreachOpen]       = useState(false)
  const [activeTab, setActiveTab]             = useState('signals')
  const [filter, setFilter]                   = useState('all')
  const [importingOrg, setImportingOrg]       = useState(false)
  const [sidebarWidth, setSidebarWidth]       = useState(272)
  const [rightWidth, setRightWidth]           = useState(300)

  function startResizeSidebar(e) {
    e.preventDefault()
    const startX = e.clientX; const startW = sidebarWidth
    function onMove(ev) { setSidebarWidth(Math.max(180, Math.min(440, startW + ev.clientX - startX))) }
    function onUp() { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp)
  }

  function startResizeRight(e) {
    e.preventDefault()
    const startX = e.clientX; const startW = rightWidth
    function onMove(ev) { setRightWidth(Math.max(200, Math.min(520, startW - (ev.clientX - startX)))) }
    function onUp() { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp)
  }

  useEffect(() => { api.getAccounts().then(setAccounts).catch(console.error) }, [])

  const selectedAccount = accounts.find(a => a.id === selectedId) || null

  useEffect(() => {
    if (!selectedId) { setSignals([]); setBriefing(null); setEngineers([]); return }
    api.getSignals(selectedId).then(setSignals).catch(() => setSignals([]))
    api.getBriefing(selectedId).then(setBriefing).catch(() => setBriefing(null))
    api.getEngineers(selectedId).then(setEngineers).catch(() => setEngineers([]))
    setActiveTab('signals')
  }, [selectedId])

  const handleSync = useCallback(async () => {
    if (!selectedId || syncing) return
    setSyncing(true)
    try {
      await api.syncAccount(selectedId)
      // Poll until backend finishes the background task
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getSyncStatus(selectedId)
        if (status.status === 'done' || status.status === 'error') break
      }
      const [accts, sigs, brf, engs] = await Promise.all([
        api.getAccounts(),
        api.getSignals(selectedId),
        api.getBriefing(selectedId).catch(() => null),
        api.getEngineers(selectedId),
      ])
      setAccounts(accts); setSignals(sigs); setBriefing(brf); setEngineers(engs)
    } catch (e) { console.error(e) }
    finally { setSyncing(false) }
  }, [selectedId, syncing])

  const handleGenerateBriefing = useCallback(async () => {
    if (!selectedId || briefingLoading) return
    setBriefingLoading(true)
    try { setBriefing(await api.generateBriefing(selectedId)) }
    catch (e) { console.error(e) }
    finally { setBriefingLoading(false) }
  }, [selectedId, briefingLoading])

  const handleAddAccount = useCallback(async (data) => {
    const acct = await api.createAccount(data)
    setAccounts(prev => [...prev, acct])
    setSelectedId(acct.id)
    setAddOpen(false)
  }, [])

  const handleDeleteAccount = useCallback(async (id) => {
    await api.deleteAccount(id)
    setAccounts(prev => prev.filter(a => a.id !== id))
    if (selectedId === id) setSelectedId(null)
  }, [selectedId])

  const handleAddEngineer = useCallback(async (username) => {
    if (!selectedId) return
    const eng = await api.addEngineer(selectedId, username)
    setEngineers(prev => [...prev, eng])
  }, [selectedId])

  const handleRemoveEngineer = useCallback(async (engId) => {
    await api.removeEngineer(engId)
    setEngineers(prev => prev.filter(e => e.id !== engId))
  }, [])

  const handleImportOrgMembers = useCallback(async () => {
    if (!selectedId || importingOrg) return
    setImportingOrg(true)
    try {
      const result = await api.importOrgMembers(selectedId)
      const engs = await api.getEngineers(selectedId)
      setEngineers(engs)
      // Auto-sync now that we have contributors
      setSyncing(true)
      await api.syncAccount(selectedId)
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getSyncStatus(selectedId)
        if (status.status === 'done' || status.status === 'error') break
      }
      const [accts, sigs, brf, freshEngs] = await Promise.all([
        api.getAccounts(),
        api.getSignals(selectedId),
        api.getBriefing(selectedId).catch(() => null),
        api.getEngineers(selectedId),
      ])
      setAccounts(accts); setSignals(sigs); setBriefing(brf); setEngineers(freshEngs)
      window.alert(`Imported ${result.added} contributors (${result.skipped} already tracked) — sync complete`)
    } catch (e) {
      window.alert(`Import failed: ${e.message}`)
    } finally {
      setImportingOrg(false)
      setSyncing(false)
    }
  }, [selectedId, importingOrg])

  const filteredAccounts = accounts.filter(a => {
    if (filter === 'clients')  return a.account_type === 'client'
    if (filter === 'pipeline') return a.account_type === 'prospect'
    return true
  })

  const score = selectedAccount?.signal_score ?? 0
  const frictionSignals = briefing?.content?.friction_signals ?? []
  const stack = briefing?.content?.tech_stack ?? []

  return (
    <div className="gp-layout">
      <TopNav accounts={accounts} onAddAccount={() => setAddOpen(true)} />
      <div className="gp-body">
        <div style={{ width: sidebarWidth, flexShrink: 0, display: 'flex' }}>
          <AccountSidebar
            accounts={filteredAccounts} selectedId={selectedId}
            onSelect={setSelectedId} onDelete={handleDeleteAccount}
            onAdd={() => setAddOpen(true)} filter={filter} onFilter={setFilter}
          />
        </div>
        <div className="resize-handle" onMouseDown={startResizeSidebar} />
        <div className="gp-main">
          {!selectedAccount ? (
            <div className="empty-state">
              <div style={{ fontSize: 32 }}>&diams;</div>
              <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 16, color: 'var(--navy)' }}>
                Select an account
              </div>
              <div style={{ color: 'var(--text-muted)', maxWidth: 280 }}>
                Choose an account from the sidebar or add a new GitHub organization to start tracking signals.
              </div>
            </div>
          ) : (
            <>
              <div className="acct-header">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{
                      width: 46, height: 46, borderRadius: 12, flexShrink: 0,
                      background: PALETTE[selectedAccount.id % 8],
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: 'var(--display)', fontWeight: 800, fontSize: 16, color: '#fff'
                    }}>{initials(selectedAccount.name || selectedAccount.github_org)}</div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 18, color: 'var(--navy)' }}>
                          {selectedAccount.name || selectedAccount.github_org}
                        </span>
                        <span style={{
                          padding: '2px 8px', borderRadius: 5, fontSize: 9, fontFamily: 'var(--mono)',
                          fontWeight: 500, letterSpacing: '0.08em',
                          background: scoreBg(score), color: scoreFg(score), border: `1px solid ${scoreBd(score)}`
                        }}>{scoreLbl(score)}</span>
                        <span style={{
                          padding: '2px 8px', borderRadius: 5, fontSize: 9, fontFamily: 'var(--mono)',
                          background: 'var(--bg)', color: 'var(--text-muted)', border: '1px solid var(--border)'
                        }}>{selectedAccount.account_type === 'client' ? 'Active Client' : 'Pipeline'}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3, fontFamily: 'var(--mono)' }}>
                        github.com/{selectedAccount.github_org}
                        {selectedAccount.last_synced && (
                          <span style={{ marginLeft: 10, color: 'var(--text-faint)' }}>
                            synced {new Date(selectedAccount.last_synced).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => setOutreachOpen(true)} style={{
                      padding: '7px 16px', borderRadius: 8, border: 'none',
                      background: 'var(--magenta)', color: '#fff', fontSize: 12,
                      fontFamily: 'var(--display)', fontWeight: 700, cursor: 'pointer'
                    }}>Draft Outreach</button>
                    <button onClick={handleSync} disabled={syncing} style={{
                      padding: '7px 16px', borderRadius: 8,
                      border: '1px solid var(--border)', background: 'var(--surface-2)',
                      color: 'var(--text-secondary)', fontSize: 12, fontFamily: 'var(--mono)',
                      cursor: syncing ? 'not-allowed' : 'pointer'
                    }}>{syncing ? 'Syncing...' : 'Sync Now'}</button>
                  </div>
                </div>
              </div>

              {syncing && (
                <div className="sync-bar"><Spinner size={12} /> Collecting signals...</div>
              )}

              {(briefing || briefingLoading) && (
                <BriefingCard briefing={briefing} loading={briefingLoading}
                  onRegenerate={handleGenerateBriefing} onOutreach={() => setOutreachOpen(true)} />
              )}

              {frictionSignals.length > 0 && (
                <div className="friction-strip">
                  <div style={{ fontSize: 10, fontWeight: 500, color: 'var(--warm-fg)', letterSpacing: '0.08em', marginBottom: 6, fontFamily: 'var(--mono)' }}>
                    FRICTION SIGNALS
                  </div>
                  {frictionSignals.map((f, i) => (
                    <div key={i} style={{ fontSize: 12, color: '#5a4010', lineHeight: 1.6, fontFamily: 'var(--mono)', fontWeight: 300 }}>
                      &mdash; {f}
                    </div>
                  ))}
                </div>
              )}

              {!briefing && !briefingLoading && (
                <div style={{ margin: '18px 28px 0' }}>
                  <button onClick={handleGenerateBriefing} style={{
                    padding: '9px 20px', borderRadius: 8, border: 'none',
                    background: 'var(--magenta)', color: '#fff', fontSize: 12,
                    fontFamily: 'var(--display)', fontWeight: 700, cursor: 'pointer'
                  }}>Generate Briefing</button>
                </div>
              )}

              <div className="gp-tabs-bar">
                {['signals', 'stack', 'engineers'].map(tab => (
                  <button key={tab}
                    className={`gp-tab-btn${activeTab === tab ? ' active' : ''}`}
                    onClick={() => setActiveTab(tab)}>{tab}</button>
                ))}
              </div>

              <div className="tab-content">
                {activeTab === 'signals' && <SignalFeed signals={signals} />}

                {activeTab === 'stack' && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {stack.length === 0
                      ? <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No stack data. Generate a briefing first.</div>
                      : stack.map((s, i) => (
                        <div key={i} className="stack-chip">
                          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#22C55E', display: 'inline-block' }} />
                          {s}
                        </div>
                      ))
                    }
                  </div>
                )}

                {activeTab === 'engineers' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    {engineers.length === 0
                      ? <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No engineers tracked yet.</div>
                      : engineers.map(eng => {
                        const engSigs = signals.filter(s => s.actor_login === eng.github_username)
                        const heat = engSigs.length > 0 ? sigHeat(engSigs[0]) : 'cool'
                        return (
                          <div key={eng.id} style={{
                            display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px',
                            borderRadius: 8, background: 'var(--surface)', border: '1px solid var(--border)'
                          }}>
                            <div style={{
                              width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                              background: heatBg(heat), border: `1px solid ${heatBd(heat)}`,
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 10, fontWeight: 700, color: heatFg(heat), fontFamily: 'var(--mono)'
                            }}>{eng.github_username.slice(0, 2).toUpperCase()}</div>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: 12, color: 'var(--navy)', fontFamily: 'var(--mono)' }}>{eng.github_username}</div>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                                {engSigs.length} signal{engSigs.length !== 1 ? 's' : ''}
                              </div>
                            </div>
                            <button onClick={() => handleRemoveEngineer(eng.id)} style={{
                              background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer', fontSize: 14
                            }}>&times;</button>
                          </div>
                        )
                      })
                    }
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <button onClick={() => {
                        const u = window.prompt('GitHub username to track:')
                        if (u && u.trim()) handleAddEngineer(u.trim())
                      }} style={{
                        flex: 1, padding: '7px 14px', borderRadius: 8,
                        border: '1px dashed var(--border)', background: 'transparent',
                        color: 'var(--text-muted)', fontSize: 11, cursor: 'pointer', fontFamily: 'var(--mono)'
                      }}>+ Track engineer</button>
                      <button onClick={handleImportOrgMembers} disabled={importingOrg} style={{
                        flex: 1, padding: '7px 14px', borderRadius: 8,
                        border: '1px solid var(--border)', background: 'var(--navy)',
                        color: '#fff', fontSize: 11, cursor: importingOrg ? 'not-allowed' : 'pointer',
                        fontFamily: 'var(--mono)', opacity: importingOrg ? 0.6 : 1
                      }}>{importingOrg ? 'Scanning repos...' : 'Import Contributors'}</button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
        <div className="resize-handle" onMouseDown={startResizeRight} />
        <div style={{ width: rightWidth, flexShrink: 0, display: 'flex' }}>
          <RightPanel account={selectedAccount} signals={signals}
            engineers={engineers} onOutreach={() => setOutreachOpen(true)} />
        </div>
      </div>
      <AddAccountDialog isOpen={addOpen} onClose={() => setAddOpen(false)} onSubmit={handleAddAccount} />
      <OutreachModal isOpen={outreachOpen} onClose={() => setOutreachOpen(false)}
        account={selectedAccount} briefing={briefing} />
    </div>
  )
}
