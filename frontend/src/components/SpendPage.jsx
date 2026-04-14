import { useState, useEffect } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from '../api'

function formatMoney(n) {
  if (!n || n === 0) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`
  return `$${n}`
}

function BarChart({ data, labelKey, valueKey, color = '#2563EB' }) {
  const max = Math.max(...data.map(d => d[valueKey]), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 120, fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-muted)', textAlign: 'right', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {d[labelKey]}
          </div>
          <div style={{ flex: 1, background: '#F1F5F9', borderRadius: 3, height: 14, overflow: 'hidden' }}>
            <div style={{
              width: `${(d[valueKey] / max) * 100}%`, height: '100%',
              background: color, borderRadius: 3, transition: 'width 0.4s ease',
            }} />
          </div>
          <div style={{ width: 60, fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--navy)', flexShrink: 0 }}>
            {formatMoney(d[valueKey])}
          </div>
        </div>
      ))}
    </div>
  )
}

function SpendRow({ row }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px',
      borderBottom: '1px solid var(--border)', background: '#fff',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--navy)', fontFamily: 'var(--mono)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.vendor}</div>
        {row.program && (
          <div style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>
            {row.program}{row.cfda ? ` · CFDA ${row.cfda}` : ''}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0, textAlign: 'right' }}>
        <div style={{ fontSize: 14, fontWeight: 800, fontFamily: 'var(--display)', color: '#166534' }}>
          {formatMoney(row.amount)}
        </div>
        {row.year > 0 && (
          <div style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)' }}>FY{row.year}</div>
        )}
      </div>
      {row.award_type && (
        <div style={{
          fontSize: 8, fontFamily: 'var(--mono)', padding: '2px 6px', borderRadius: 4,
          background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE',
          fontWeight: 700, flexShrink: 0,
        }}>{row.award_type}</div>
      )}
    </div>
  )
}

export default function SpendPage({ accounts = [] }) {
  const [selectedId, setSelectedId] = useState(accounts[0]?.id || null)
  const [spend, setSpend] = useState([])
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    if (accounts.length > 0 && !selectedId) setSelectedId(accounts[0].id)
  }, [accounts])

  useEffect(() => {
    if (selectedId) loadSpend(selectedId)
    else setSpend([])
  }, [selectedId])

  async function loadSpend(id) {
    setLoading(true)
    try { setSpend(await api.getSpend(id)) }
    catch { setSpend([]) }
    finally { setLoading(false) }
  }

  async function scan() {
    if (!selectedId || scanning) return
    setScanning(true)
    try {
      await api.scanSpend(selectedId)
      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const fresh = await api.getSpend(selectedId)
        if (fresh.length > 0) { setSpend(fresh); break }
      }
      setSpend(await api.getSpend(selectedId))
    } catch (e) { alert(`Scan failed: ${e.message}`) }
    finally { setScanning(false) }
  }

  const selectedAccount = accounts.find(a => a.id === selectedId)

  // Aggregations
  const totalSpend = spend.reduce((s, r) => s + (r.amount || 0), 0)
  const byVendor = Object.values(
    spend.reduce((acc, r) => {
      const k = r.vendor
      acc[k] = acc[k] || { vendor: k, total: 0 }
      acc[k].total += r.amount || 0
      return acc
    }, {})
  ).sort((a, b) => b.total - a.total).slice(0, 8)

  const byYear = Object.values(
    spend.filter(r => r.year > 0).reduce((acc, r) => {
      const k = r.year
      acc[k] = acc[k] || { year: k, total: 0 }
      acc[k].total += r.amount || 0
      return acc
    }, {})
  ).sort((a, b) => b.year - a.year).slice(0, 6)

  const edtechVendors = ['Google', 'Microsoft', 'Apple', 'Canvas', 'Instructure', 'PowerSchool',
    'Amplify', 'Renaissance', 'DreamBox', 'Pearson', 'McGraw-Hill', 'Houghton Mifflin',
    'Clever', 'ClassLink', 'Schoology', 'Edmodo']
  const edtechSpend = spend.filter(r => edtechVendors.some(v => r.vendor?.includes(v)))
  const edtechTotal = edtechSpend.reduce((s, r) => s + (r.amount || 0), 0)

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', background: 'var(--bg)' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.12em', marginBottom: 6 }}>PROCUREMENT INTELLIGENCE</div>
        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 22, color: 'var(--navy)', margin: 0 }}>Public Spend Intelligence</h1>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: 6 }}>
          360° view of what districts spend on technology and EdTech vendors. Data sourced from USASpending.gov.
        </p>
      </div>

      {/* Account picker */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 24, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>DISTRICT</span>
        <select value={selectedId || ''} onChange={e => setSelectedId(parseInt(e.target.value))}
          style={{ fontSize: 12, fontFamily: 'var(--mono)', padding: '6px 12px', borderRadius: 7, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--navy)' }}>
          {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <button onClick={scan} disabled={scanning || !selectedId} style={{
          padding: '7px 16px', borderRadius: 8, border: 'none', cursor: scanning ? 'not-allowed' : 'pointer',
          background: 'var(--navy)', color: '#fff', fontFamily: 'var(--mono)', fontSize: 10, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 6, opacity: scanning ? 0.7 : 1,
        }}>
          {scanning && <Spinner size={10} />}
          {scanning ? 'Scanning USASpending...' : '↻ Refresh Spend Data'}
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
      ) : spend.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>💰</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)', marginBottom: 6 }}>No spend data yet</div>
          <div style={{ fontSize: 12 }}>
            {selectedAccount?.district_legal_name
              ? `Click "Refresh Spend Data" to pull federal awards for ${selectedAccount.district_legal_name}.`
              : 'Select a district and click "Refresh Spend Data" to pull USASpending.gov data.'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-faint)', marginTop: 6 }}>
            Note: requires the district's official legal name to match USASpending.gov records.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px,1fr))', gap: 12 }}>
            {[
              { label: 'TOTAL AWARDS', value: formatMoney(totalSpend) },
              { label: 'EDTECH SPEND', value: formatMoney(edtechTotal) },
              { label: 'AGENCIES', value: byVendor.length },
              { label: 'AWARD RECORDS', value: spend.length },
            ].map(m => (
              <div key={m.label} style={{ padding: '14px 16px', borderRadius: 9, background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 4 }}>{m.label}</div>
                <div style={{ fontSize: 20, fontWeight: 800, fontFamily: 'var(--display)', color: 'var(--navy)' }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Top agencies */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
              <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 14 }}>TOP AWARDING AGENCIES</div>
              <BarChart data={byVendor} labelKey="vendor" valueKey="total" color="#2563EB" />
            </div>

            {/* By year */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
              <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--text-faint)', letterSpacing: '0.1em', marginBottom: 14 }}>AWARDS BY FISCAL YEAR</div>
              <BarChart data={byYear.map(d => ({ year: `FY${d.year}`, total: d.total }))} labelKey="year" valueKey="total" color="#C8005A" />
            </div>
          </div>

          {/* Award table */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--text-faint)', letterSpacing: '0.1em' }}>
              ALL FEDERAL AWARDS — {spend.length} RECORDS
            </div>
            {spend.map((row, i) => <SpendRow key={i} row={row} />)}
          </div>

        </div>
      )}
    </div>
  )
}
