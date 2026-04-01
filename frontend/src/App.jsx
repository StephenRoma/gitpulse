import { useEffect, useState, useCallback } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from './api'
import TopNav from './components/TopNav'
import AccountLogo from './components/AccountLogo'
import AccountSidebar from './components/AccountSidebar'
import BriefingCard from './components/BriefingCard'
import SignalFeed from './components/SignalFeed'
import RightPanel from './components/RightPanel'
import AddAccountDialog from './components/AddAccountDialog'
import EditAccountDialog from './components/EditAccountDialog'
import OutreachModal from './components/OutreachModal'
import ReportModal from './components/ReportModal'
import DashboardPage from './components/DashboardPage'

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
  const [editOpen, setEditOpen]               = useState(false)
  const [editAccount, setEditAccount]         = useState(null)
  const [teams, setTeams]                     = useState([])
  const [addTeamOpen, setAddTeamOpen]         = useState(false)
  const [newTeamName, setNewTeamName]         = useState('')
  const [newTeamColor, setNewTeamColor]       = useState('#1A2158')
  const [signalTags, setSignalTags]           = useState({})  // {signal_id: [theme, ...]}
  const [reportOpen, setReportOpen]           = useState(false)
  const [reportData, setReportData]           = useState(null)
  const [reportLoading, setReportLoading]     = useState(false)
  const [page, setPage]                       = useState(() => localStorage.getItem('gp_page') || 'dashboard')
  const [stages, setStagesState]              = useState(() => {
    try { return JSON.parse(localStorage.getItem('gitpulse_stages') || '{}') } catch { return {} }
  })
  const [hotSignals, setHotSignals]           = useState([])
  const [hotLoading, setHotLoading]           = useState(false)

  function setStage(accountId, stageKey) {
    setStagesState(prev => {
      const next = { ...prev, [accountId]: stageKey }
      localStorage.setItem('gitpulse_stages', JSON.stringify(next))
      return next
    })
  }

  function handlePageChange(p) {
    setPage(p)
    localStorage.setItem('gp_page', p)
  }

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

  useEffect(() => {
    api.getAccounts().then(accts => {
      setAccounts(accts)
      if (accts.length > 0) {
        const saved = parseInt(localStorage.getItem('gp_selected_id'))
        const match = accts.find(a => a.id === saved)
        setSelectedId(match ? match.id : accts[0].id)
      }
    }).catch(console.error)
    // Fetch hot signals for dashboard
    setHotLoading(true)
    api.getHotSignals(15).then(setHotSignals).catch(() => setHotSignals([])).finally(() => setHotLoading(false))
  }, [])

  // Refresh hot signals whenever we return to dashboard
  useEffect(() => {
    if (page === 'dashboard') {
      setHotLoading(true)
      api.getHotSignals(15).then(setHotSignals).catch(() => setHotSignals([])).finally(() => setHotLoading(false))
    }
  }, [page])

  function handleSelectAccount(id) {
    setSelectedId(id)
    handlePageChange('accounts')
  }

  const selectedAccount = accounts.find(a => a.id === selectedId) || null

  // Persist selected account across refreshes
  useEffect(() => {
    if (selectedId) localStorage.setItem('gp_selected_id', selectedId)
  }, [selectedId])

  useEffect(() => {
    if (!selectedId) { setSignals([]); setBriefing(null); setEngineers([]); setTeams([]); return }
    api.getSignals(selectedId).then(setSignals).catch(() => setSignals([]))
    api.getBriefing(selectedId).then(setBriefing).catch(() => setBriefing(null))
    api.getEngineers(selectedId).then(setEngineers).catch(() => setEngineers([]))
    api.getTeams(selectedId).then(setTeams).catch(() => setTeams([]))
    api.getSignalTags(selectedId).then(setSignalTags).catch(() => setSignalTags({}))
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

  const handleEditAccount = useCallback(async (data) => {
    const updated = await api.updateAccount(editAccount.id, data)
    setAccounts(prev => prev.map(a => a.id === updated.id ? { ...a, ...updated } : a))
    setEditOpen(false)
    setEditAccount(null)
  }, [editAccount])

  const handleCreateTeam = useCallback(async () => {
    if (!selectedId || !newTeamName.trim()) return
    const team = await api.createTeam(selectedId, { name: newTeamName.trim(), color: newTeamColor })
    setTeams(prev => [...prev, team])
    setNewTeamName('')
    setNewTeamColor('#1A2158')
    setAddTeamOpen(false)
  }, [selectedId, newTeamName, newTeamColor])

  const handleDeleteTeam = useCallback(async (teamId) => {
    await api.deleteTeam(teamId)
    setTeams(prev => prev.filter(t => t.id !== teamId))
    setEngineers(prev => prev.map(e => e.team_id === teamId ? { ...e, team_id: null } : e))
  }, [])

  const handleAssignTeam = useCallback(async (engineerId, teamIdStr) => {
    const teamId = teamIdStr === '' ? null : parseInt(teamIdStr)
    await api.assignEngineerTeam(engineerId, teamId)
    setEngineers(prev => prev.map(e => e.id === engineerId ? { ...e, team_id: teamId } : e))
  }, [])

  const handleTagSignal = useCallback(async (signalId, theme) => {
    // Optimistic update
    setSignalTags(prev => {
      const existing = prev[signalId] || []
      if (existing.includes(theme)) return prev
      return { ...prev, [signalId]: [...existing, theme] }
    })
    try { await api.tagSignal(signalId, theme) }
    catch (e) {
      // Rollback
      setSignalTags(prev => ({ ...prev, [signalId]: (prev[signalId] || []).filter(t => t !== theme) }))
    }
  }, [])

  const handleUntagSignal = useCallback(async (signalId, theme) => {
    setSignalTags(prev => ({ ...prev, [signalId]: (prev[signalId] || []).filter(t => t !== theme) }))
    try { await api.untagSignal(signalId, theme) }
    catch (e) {
      // Rollback — re-fetch from server
      api.getSignalTags(selectedId).then(setSignalTags).catch(() => {})
    }
  }, [selectedId])

  const handleGenerateReport = useCallback(async () => {
    if (!selectedId || reportLoading) return
    setReportLoading(true)
    setReportOpen(true)
    try {
      await api.generateReport(selectedId)
      // Poll until done
      let tries = 0
      while (tries < 60) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getReportStatus(selectedId)
        if (status.status === 'done') {
          const data = await api.getReport(selectedId)
          setReportData(data?.content ?? data)
          break
        } else if (status.status === 'error') {
          window.alert(`Report generation failed: ${status.detail}`)
          setReportOpen(false)
          break
        }
        tries++
      }
    } catch (e) {
      window.alert(`Report generation failed: ${e.message}`)
      setReportOpen(false)
    } finally {
      setReportLoading(false)
    }
  }, [selectedId, reportLoading])

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
      // If backend suggests teams from company data, prompt user
      if (result.suggested_teams?.length > 0) {
        const msg = `Imported ${result.added} contributors.\n\nDetected companies: ${result.suggested_teams.join(', ')}\n\nCreate teams from these? (Go to Engineers tab to manage teams)`
        window.alert(msg)
      }
      // Auto-sync now that we have contributors
      setSyncing(true)
      await api.syncAccount(selectedId)
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getSyncStatus(selectedId)
        if (status.status === 'done' || status.status === 'error') break
      }
      const [accts, sigs, brf, freshEngs, freshTeams] = await Promise.all([
        api.getAccounts(),
        api.getSignals(selectedId),
        api.getBriefing(selectedId).catch(() => null),
        api.getEngineers(selectedId),
        api.getTeams(selectedId),
      ])
      setAccounts(accts); setSignals(sigs); setBriefing(brf); setEngineers(freshEngs); setTeams(freshTeams)
      if (!result.suggested_teams?.length) {
        window.alert(`Imported ${result.added} contributors (${result.skipped} already tracked) — sync complete`)
      }
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
      <TopNav accounts={accounts} onAddAccount={() => setAddOpen(true)} page={page} onPageChange={handlePageChange} />

      {/* ── Dashboard page ─────────────────────────────────────────── */}
      {page === 'dashboard' && (
        <div className="gp-body" style={{ overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <DashboardPage
              accounts={accounts}
              stages={stages}
              onSetStage={setStage}
              hotSignals={hotSignals}
              hotLoading={hotLoading}
              onSelectAccount={handleSelectAccount}
              onSyncAll={() => api.syncAll()}
            />
          </div>
        </div>
      )}

      {/* ── Accounts page ──────────────────────────────────────────── */}
      {page === 'accounts' && (
      <div className="gp-body">
        <div style={{ width: sidebarWidth, flexShrink: 0, display: 'flex' }}>
          <AccountSidebar
            accounts={filteredAccounts} selectedId={selectedId}
            onSelect={setSelectedId} onDelete={handleDeleteAccount}
            onEdit={(acc) => { setEditAccount(acc); setEditOpen(true) }}
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
                    <AccountLogo account={selectedAccount} size={46} radius={12} />
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
                    <button onClick={() => { setEditAccount(selectedAccount); setEditOpen(true) }} style={{
                      padding: '7px 14px', borderRadius: 8,
                      border: '1px solid var(--border)', background: 'var(--surface-2)',
                      color: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--mono)',
                      cursor: 'pointer'
                    }}>&#9998; Edit</button>
                    <button onClick={handleGenerateReport} disabled={reportLoading} style={{
                      padding: '7px 14px', borderRadius: 8,
                      border: '1px solid var(--border)', background: 'var(--surface-2)',
                      color: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--mono)',
                      cursor: reportLoading ? 'not-allowed' : 'pointer',
                      opacity: reportLoading ? 0.6 : 1,
                    }}>{reportLoading ? 'Generating...' : '&#128196; Report'}</button>
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
                {activeTab === 'signals' && <SignalFeed signals={signals} engineers={engineers}
                  signalTags={signalTags} onTagSignal={handleTagSignal} onUntagSignal={handleUntagSignal} />}

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
                    {/* Team management header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', letterSpacing: '0.08em' }}>
                        TEAMS ({teams.length})
                      </span>
                      {!addTeamOpen && (
                        <button onClick={() => setAddTeamOpen(true)} style={{
                          fontSize: 10, fontFamily: 'var(--mono)', border: '1px dashed var(--border)',
                          borderRadius: 6, padding: '3px 10px', background: 'transparent',
                          color: 'var(--text-muted)', cursor: 'pointer'
                        }}>+ Add Team</button>
                      )}
                    </div>

                    {/* New team inline form */}
                    {addTeamOpen && (
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '8px 10px',
                        borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', marginBottom: 4 }}>
                        <input value={newTeamName} onChange={e => setNewTeamName(e.target.value)}
                          placeholder="Team name (e.g. Capital Markets)"
                          onKeyDown={e => { if (e.key === 'Enter') handleCreateTeam(); if (e.key === 'Escape') setAddTeamOpen(false) }}
                          style={{ flex: 1, fontSize: 11, fontFamily: 'var(--mono)', border: '1px solid var(--border)',
                            borderRadius: 4, padding: '4px 8px', background: 'var(--bg)', color: 'var(--navy)' }}
                          autoFocus
                        />
                        <input type="color" value={newTeamColor} onChange={e => setNewTeamColor(e.target.value)}
                          title="Team color"
                          style={{ width: 28, height: 28, border: '1px solid var(--border)', borderRadius: 4,
                            padding: 2, cursor: 'pointer', background: 'none' }}
                        />
                        <button onClick={handleCreateTeam} style={{
                          fontSize: 10, fontFamily: 'var(--mono)', border: 'none', borderRadius: 4,
                          padding: '4px 10px', background: 'var(--navy)', color: '#fff', cursor: 'pointer'
                        }}>Save</button>
                        <button onClick={() => { setAddTeamOpen(false); setNewTeamName('') }} style={{
                          fontSize: 10, fontFamily: 'var(--mono)', border: '1px solid var(--border)',
                          borderRadius: 4, padding: '4px 8px', background: 'transparent',
                          color: 'var(--text-muted)', cursor: 'pointer'
                        }}>Cancel</button>
                      </div>
                    )}

                    {/* Engineers grouped by team */}
                    {(() => {
                      const teamMap = Object.fromEntries(teams.map(t => [t.id, t]))
                      const grouped = {}
                      const unassigned = []
                      for (const eng of engineers) {
                        if (eng.team_id && teamMap[eng.team_id]) {
                          if (!grouped[eng.team_id]) grouped[eng.team_id] = []
                          grouped[eng.team_id].push(eng)
                        } else {
                          unassigned.push(eng)
                        }
                      }

                      const teamDropdown = (eng) => (
                        <select value={eng.team_id || ''}
                          onChange={e => handleAssignTeam(eng.id, e.target.value)}
                          onClick={e => e.stopPropagation()}
                          style={{ fontSize: 9, fontFamily: 'var(--mono)', border: '1px solid var(--border)',
                            borderRadius: 4, padding: '2px 4px', background: 'var(--surface)',
                            color: 'var(--text-muted)', cursor: 'pointer', maxWidth: 110 }}
                        >
                          <option value="">No Team</option>
                          {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                      )

                      const engRow = (eng) => {
                        const engSigs = signals.filter(s => s.actor_login === eng.github_username)
                        const heat = engSigs.length > 0 ? sigHeat(engSigs[0]) : 'cool'
                        return (
                          <div key={eng.id} style={{
                            display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px',
                            borderRadius: 7, background: 'var(--surface)', border: '1px solid var(--border)'
                          }}>
                            <div style={{
                              width: 28, height: 28, borderRadius: 7, flexShrink: 0,
                              background: heatBg(heat), border: `1px solid ${heatBd(heat)}`,
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 9, fontWeight: 700, color: heatFg(heat), fontFamily: 'var(--mono)'
                            }}>{eng.github_username.slice(0, 2).toUpperCase()}</div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: 11, color: 'var(--navy)', fontFamily: 'var(--mono)' }}>{eng.github_username}</div>
                              {eng.company && (
                                <div style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)',
                                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{eng.company}</div>
                              )}
                            </div>
                            {teamDropdown(eng)}
                            <button onClick={() => handleRemoveEngineer(eng.id)} style={{
                              background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer', fontSize: 13, flexShrink: 0
                            }}>&times;</button>
                          </div>
                        )
                      }

                      return (
                        <>
                          {teams.map(team => (
                            <div key={team.id} style={{ marginBottom: 6 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 8px',
                                borderRadius: '7px 7px 0 0', background: team.color + '18',
                                border: `1px solid ${team.color}40`, borderBottom: 'none' }}>
                                <div style={{ width: 8, height: 8, borderRadius: '50%', background: team.color, flexShrink: 0 }} />
                                <span style={{ flex: 1, fontSize: 10, fontWeight: 700, color: team.color,
                                  fontFamily: 'var(--display)', letterSpacing: '0.05em' }}>
                                  {team.name.toUpperCase()}
                                </span>
                                <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
                                  {(grouped[team.id] || []).length} engineers
                                </span>
                                <button onClick={() => handleDeleteTeam(team.id)}
                                  title="Delete team (engineers become unassigned)"
                                  style={{ background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--text-faint)', fontSize: 11, padding: '0 2px' }}>&times;</button>
                              </div>
                              <div style={{ border: `1px solid ${team.color}40`, borderTop: 'none',
                                borderRadius: '0 0 7px 7px', overflow: 'hidden' }}>
                                {(grouped[team.id] || []).length === 0
                                  ? <div style={{ padding: '8px 12px', fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>No engineers assigned yet</div>
                                  : (grouped[team.id] || []).map(engRow)
                                }
                              </div>
                            </div>
                          ))}

                          {/* Unassigned group */}
                          {unassigned.length > 0 && (
                            <div style={{ marginBottom: 6 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 8px',
                                borderRadius: '7px 7px 0 0', background: 'var(--bg)',
                                border: '1px solid var(--border)', borderBottom: 'none' }}>
                                <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
                                  fontFamily: 'var(--display)', letterSpacing: '0.05em', flex: 1 }}>UNASSIGNED</span>
                                <span style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
                                  {unassigned.length} engineers
                                </span>
                              </div>
                              <div style={{ border: '1px solid var(--border)', borderTop: 'none', borderRadius: '0 0 7px 7px', overflow: 'hidden' }}>
                                {unassigned.map(engRow)}
                              </div>
                            </div>
                          )}

                          {engineers.length === 0 && (
                            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No engineers tracked yet.</div>
                          )}
                        </>
                      )
                    })()}

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
            engineers={engineers} teams={teams} onOutreach={() => setOutreachOpen(true)} />
        </div>
      </div>
      )}
      <AddAccountDialog isOpen={addOpen} onClose={() => setAddOpen(false)} onSubmit={handleAddAccount} />
      <EditAccountDialog isOpen={editOpen} onClose={() => { setEditOpen(false); setEditAccount(null) }}
        account={editAccount} onSubmit={handleEditAccount} />
      <OutreachModal isOpen={outreachOpen} onClose={() => setOutreachOpen(false)}
        account={selectedAccount} briefing={briefing} />
      <ReportModal
        isOpen={reportOpen} onClose={() => setReportOpen(false)}
        report={reportData} loading={reportLoading}
        account={selectedAccount}
      />
    </div>
  )
}
