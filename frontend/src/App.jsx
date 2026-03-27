import { useEffect, useState, useCallback, useRef } from 'react'
import { Tabs, Tab, Spinner, NonIdealState, Button, Intent } from '@blueprintjs/core'

import { api } from './api'
import TopNav from './components/TopNav'
import AccountSidebar from './components/AccountSidebar'
import BriefingCard from './components/BriefingCard'
import SignalFeed from './components/SignalFeed'
import RightPanel from './components/RightPanel'
import AddAccountDialog from './components/AddAccountDialog'

export default function App() {
  const [accounts, setAccounts] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [signals, setSignals] = useState([])
  const [engineers, setEngineers] = useState([])
  const [briefing, setBriefing] = useState(null)
  const [syncStatus, setSyncStatus] = useState({})
  const [loading, setLoading] = useState({ accounts: true, signals: false })
  const [addOpen, setAddOpen] = useState(false)
  const [apiHealth, setApiHealth] = useState(false)
  const [activeTab, setActiveTab] = useState('signals')

  const syncPollRef = useRef({})

  // ── Boot ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAccounts()
    api.health().then(h => setApiHealth(h?.status === 'ok')).catch(() => {})
  }, [])

  async function fetchAccounts() {
    setLoading(l => ({ ...l, accounts: true }))
    try {
      const data = await api.getAccounts()
      setAccounts(data)
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id)
      }
    } finally {
      setLoading(l => ({ ...l, accounts: false }))
    }
  }

  // ── Account selection ─────────────────────────────────────────────
  useEffect(() => {
    if (!selectedId) return
    fetchAccountData(selectedId)
  }, [selectedId])

  async function fetchAccountData(id) {
    setLoading(l => ({ ...l, signals: true }))
    setBriefing(null)
    setSignals([])
    setEngineers([])
    try {
      const [sigs, engs, brief, status] = await Promise.all([
        api.getSignals(id, 100),
        api.getEngineers(id),
        api.getBriefing(id),
        api.getSyncStatus(id)
      ])
      setSignals(sigs)
      setEngineers(engs)
      setBriefing(brief)
      setSyncStatus(s => ({ ...s, [id]: status }))
    } finally {
      setLoading(l => ({ ...l, signals: false }))
    }
  }

  // ── Sync ──────────────────────────────────────────────────────────
  async function handleSync(id) {
    const targetId = id || selectedId
    if (!targetId) return

    setSyncStatus(s => ({ ...s, [targetId]: { status: 'syncing', detail: 'Starting sync…' } }))
    await api.syncAccount(targetId)

    // Poll status
    if (syncPollRef.current[targetId]) clearInterval(syncPollRef.current[targetId])
    syncPollRef.current[targetId] = setInterval(async () => {
      try {
        const status = await api.getSyncStatus(targetId)
        setSyncStatus(s => ({ ...s, [targetId]: status }))

        if (status.status === 'done' || status.status === 'error') {
          clearInterval(syncPollRef.current[targetId])
          fetchAccountData(targetId)
          fetchAccounts()
        }
      } catch {
        clearInterval(syncPollRef.current[targetId])
      }
    }, 2000)
  }

  // ── Account created ───────────────────────────────────────────────
  async function handleAccountCreated(newId) {
    setAddOpen(false)
    await fetchAccounts()
    setSelectedId(newId)
  }

  // ── Selected account ──────────────────────────────────────────────
  const selectedAccount = accounts.find(a => a.id === selectedId)
  const currentSyncStatus = syncStatus[selectedId]
  const isSyncing = currentSyncStatus?.status === 'syncing' || currentSyncStatus?.status === 'briefing'

  // ── Computed: tech stack from signals ─────────────────────────────
  const techStack = (() => {
    const map = {}
    for (const s of signals) {
      for (const t of (s.repo_topics || [])) {
        map[t] = (map[t] || 0) + 1
      }
      if (s.repo_language) map[s.repo_language] = (map[s.repo_language] || 0) + 1
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 10)
  })()

  return (
    <div className="gp-layout bp5-dark">
      {/* Top Nav */}
      <TopNav
        onSyncAll={() => { fetchAccounts(); if (selectedId) fetchAccountData(selectedId) }}
        onAddAccount={() => setAddOpen(true)}
        apiHealth={apiHealth}
      />

      {/* Sidebar */}
      <AccountSidebar
        accounts={accounts}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onRefresh={fetchAccounts}
      />

      {/* Main content */}
      <div className="gp-main">
        {loading.accounts && !selectedId ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
            <Spinner size={32} />
          </div>
        ) : !selectedId ? (
          <div className="empty-state">
            <div style={{ fontSize: 40 }}>⚡</div>
            <h3>No account selected</h3>
            <p>Add a prospect or client to start collecting GitHub intelligence signals.</p>
            <Button intent={Intent.PRIMARY} icon="plus" text="Add Account" onClick={() => setAddOpen(true)} />
          </div>
        ) : (
          <>
            {/* Sync status bar */}
            {isSyncing && (
              <div className="sync-bar">
                <Spinner size={12} />
                {currentSyncStatus?.detail || 'Syncing…'}
              </div>
            )}

            {/* Account header */}
            <div className="section-header" style={{ marginBottom: 20 }}>
              <div>
                <div className="section-title">
                  {selectedAccount?.name}
                  <span style={{
                    fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 400,
                    color: selectedAccount?.account_type === 'client' ? 'var(--green)' : 'var(--magenta)',
                    background: selectedAccount?.account_type === 'client'
                      ? 'rgba(35,209,139,0.1)' : 'var(--magenta-glow)',
                    padding: '2px 8px', borderRadius: 4,
                    border: `1px solid ${selectedAccount?.account_type === 'client'
                      ? 'rgba(35,209,139,0.2)' : 'rgba(233,30,140,0.2)'}`
                  }}>
                    {selectedAccount?.account_type}
                  </span>
                </div>
                <div className="section-subtitle">
                  {selectedAccount?.github_org && `@${selectedAccount.github_org} · `}
                  {signals.length} signals · {engineers.length} engineers tracked
                  {selectedAccount?.last_synced && ` · synced ${new Date(selectedAccount.last_synced + 'Z').toLocaleString()}`}
                </div>
              </div>
            </div>

            {/* Briefing card always at top */}
            <BriefingCard
              accountId={selectedId}
              briefing={briefing}
              onRefresh={() => fetchAccountData(selectedId)}
            />

            {/* Tabs: Signals / Stack */}
            <Tabs
              id="main-tabs"
              selectedTabId={activeTab}
              onChange={setActiveTab}
              className="bp5-dark"
            >
              <Tab id="signals" title={`Signals (${signals.length})`} />
              <Tab id="stack" title="Tech Stack" />
            </Tabs>

            {activeTab === 'signals' && (
              <SignalFeed signals={signals} loading={loading.signals} />
            )}

            {activeTab === 'stack' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                {techStack.length === 0 ? (
                  <div style={{ gridColumn: '1/-1', color: 'var(--text-muted)', fontSize: 13, padding: 20 }}>
                    No stack data yet. Run a sync to analyze technology signals.
                  </div>
                ) : techStack.map(([tech, count]) => (
                  <div key={tech} className="stack-chip" style={{ padding: '10px 14px', borderRadius: 8 }}>
                    <span className="stack-chip-name" style={{ fontSize: 13 }}>{tech}</span>
                    <span className="stack-chip-count">{count} signal{count !== 1 ? 's' : ''}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Right panel */}
      {selectedId && selectedAccount && (
        <RightPanel
          account={selectedAccount}
          engineers={engineers}
          signals={signals}
          onRefresh={() => fetchAccountData(selectedId)}
          syncStatus={currentSyncStatus}
          onSync={() => handleSync(selectedId)}
        />
      )}

      {/* Add Account dialog */}
      <AddAccountDialog
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={handleAccountCreated}
      />
    </div>
  )
}
