import { useEffect, useState } from 'react'
import { api } from './api'
import TopNav from './components/TopNav'
import DashboardPage from './components/DashboardPage'
import TexasPage from './components/TexasPage'

export default function App() {
  const [accounts, setAccounts] = useState([])
  const [page, setPage] = useState(() => localStorage.getItem('gp_page') || 'texas')
  const [stages, setStagesState] = useState(() => {
    try { return JSON.parse(localStorage.getItem('quorum_stages') || '{}') } catch { return {} }
  })

  function setStage(accountId, stageKey) {
    setStagesState(prev => {
      const next = { ...prev, [accountId]: stageKey }
      localStorage.setItem('quorum_stages', JSON.stringify(next))
      return next
    })
  }

  function handlePageChange(p) {
    setPage(p)
    localStorage.setItem('gp_page', p)
  }

  useEffect(() => {
    api.getAccounts().then(setAccounts).catch(() => setAccounts([]))
  }, [])

  useEffect(() => {
    if (page === 'dashboard') {
      api.getAccounts().then(setAccounts).catch(() => setAccounts([]))
    }
  }, [page])

  function handleDistrictAddedToPipeline() {
    api.getAccounts().then(setAccounts).catch(() => setAccounts([]))
  }

  return (
    <div className="gp-layout">
      <TopNav page={page} onPageChange={handlePageChange} />

      {page === 'dashboard' && (
        <div className="gp-body" style={{ overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <DashboardPage
              accounts={accounts}
              stages={stages}
              onSetStage={setStage}
              hotSignals={[]}
              hotLoading={false}
              onSelectAccount={() => handlePageChange('texas')}
              onSyncAll={() => {}}
            />
          </div>
        </div>
      )}

      {page === 'texas' && (
        <div className="gp-body" style={{ overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <TexasPage onDistrictAddedToPipeline={handleDistrictAddedToPipeline} />
          </div>
        </div>
      )}
    </div>
  )
}
