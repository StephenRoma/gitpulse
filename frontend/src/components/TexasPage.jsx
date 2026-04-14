import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api'
import TexasReportModal from './TexasReportModal'
import TexasClientReportModal from './TexasClientReportModal'

const ESC_REGIONS = Array.from({ length: 20 }, (_, i) => i + 1)

const REGION_CITIES = {
  1: 'Edinburg', 2: 'Corpus Christi', 3: 'Victoria', 4: 'Houston',
  5: 'Beaumont', 6: 'Huntsville', 7: 'Kilgore', 8: 'Mt. Pleasant',
  9: 'Wichita Falls', 10: 'Richardson', 11: 'Fort Worth', 12: 'Waco',
  13: 'Austin', 14: 'Abilene', 15: 'San Angelo', 16: 'Amarillo',
  17: 'Lubbock', 18: 'Midland', 19: 'El Paso', 20: 'San Antonio',
}

function scoreColor(score) {
  if (score >= 60) return { fg: '#C8005A', bg: '#FFF0F5', bd: '#FBCFE8' }
  if (score >= 40) return { fg: '#B45309', bg: '#FFFBEB', bd: '#FDE68A' }
  if (score >= 20) return { fg: '#0369A1', bg: '#EFF6FF', bd: '#BFDBFE' }
  return { fg: '#6B7280', bg: '#F9FAFB', bd: '#E5E7EB' }
}

function ratingColor(rating) {
  if (!rating) return { fg: '#6B7280', bg: '#F9FAFB', bd: '#E5E7EB' }
  if (rating === 'IR' || rating === 'F') return { fg: '#B91C1C', bg: '#FEF2F2', bd: '#FECACA' }
  if (rating === 'D') return { fg: '#B45309', bg: '#FFFBEB', bd: '#FDE68A' }
  if (rating === 'C') return { fg: '#0369A1', bg: '#EFF6FF', bd: '#BFDBFE' }
  if (rating === 'A' || rating === 'B') return { fg: '#166534', bg: '#F0FDF4', bd: '#BBF7D0' }
  return { fg: '#6B7280', bg: '#F9FAFB', bd: '#E5E7EB' }
}

function ratingLabel(rating) {
  if (!rating) return '—'
  if (rating === 'IR') return 'Improv. Required'
  if (rating === 'NR') return 'Not Rated'
  return rating
}

function Badge({ label, fg, bg, bd }) {
  return (
    <span style={{
      display: 'inline-block', fontSize: 9, fontWeight: 700, padding: '2px 6px',
      borderRadius: 4, background: bg, color: fg, border: `1px solid ${bd}`,
      fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap',
    }}>{label}</span>
  )
}

export default function TexasPage({ onDistrictAddedToPipeline }) {
  const [selectedRegion, setSelectedRegion] = useState(null)
  const [districts, setDistricts]           = useState([])
  const [scanStatus, setScanStatus]         = useState(null)   // null | {status, detail, ...}
  const [scanning, setScanning]             = useState(false)
  const [loading, setLoading]               = useState(false)
  const [filter, setFilter]                 = useState('troubled') // all | troubled
  const [reportDistrict, setReportDistrict] = useState(null)
  const [reportLoading, setReportLoading]   = useState(false)
  const pollRef = useRef(null)
  const [pipelineIds, setPipelineIds]               = useState(new Set())
  const [pipelining, setPipelining]                 = useState(null)
  const [clientReportDistrict, setClientReportDistrict] = useState(null)
  const [clientReportLoading, setClientReportLoading]   = useState(false)

  // Load districts when region selected and already scanned
  useEffect(() => {
    if (!selectedRegion) return
    setLoading(true)
    api.getTexasDistricts(selectedRegion)
      .then(d => { setDistricts(d || []); setLoading(false) })
      .catch(() => { setDistricts([]); setLoading(false) })
  }, [selectedRegion])

  const stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }, [])

  const handleScan = useCallback(async () => {
    if (!selectedRegion || scanning) return
    setScanning(true)
    setScanStatus({ status: 'starting', detail: 'Starting scan...' })
    setDistricts([])
    try {
      await api.scanTexasRegion(selectedRegion)
      // Poll for progress
      pollRef.current = setInterval(async () => {
        try {
          const status = await api.getTexasScanStatus(selectedRegion)
          setScanStatus(status)
          if (status.status === 'done' || status.status === 'error') {
            stopPoll()
            setScanning(false)
            if (status.status === 'done') {
              const fresh = await api.getTexasDistricts(selectedRegion)
              setDistricts(fresh || [])
            }
          }
        } catch {
          stopPoll()
          setScanning(false)
        }
      }, 2500)
    } catch (e) {
      setScanStatus({ status: 'error', detail: e.message })
      setScanning(false)
    }
  }, [selectedRegion, scanning, stopPoll])

  const handleAddToPipeline = useCallback(async (district) => {
    if (pipelineIds.has(district.district_id) || district.account_id) return
    setPipelining(district.district_id)
    try {
      await api.addTexasDistrictToPipeline(district.district_id)
      setPipelineIds(prev => new Set([...prev, district.district_id]))
      setDistricts(prev => prev.map(d =>
        d.district_id === district.district_id ? { ...d, account_id: true } : d
      ))
      onDistrictAddedToPipeline?.()
    } catch (e) {
      window.alert(`Failed to add to pipeline: ${e.message}`)
    } finally {
      setPipelining(null)
    }
  }, [pipelineIds, onDistrictAddedToPipeline])

  const handleOpenReport = useCallback(async (district) => {
    if (district.babbage_pitch) {
      setReportDistrict(district)
      return
    }
    // Generate pitch first
    setReportLoading(true)
    setReportDistrict({ ...district, _generating: true })
    try {
      await api.generateTexasReport(district.district_id)
      // Poll until done
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getTexasReportStatus(district.district_id)
        if (status.status === 'done') {
          const fresh = await api.getTexasDistrict(district.district_id)
          setReportDistrict(fresh)
          // Update in list
          setDistricts(prev => prev.map(d =>
            d.district_id === district.district_id ? fresh : d
          ))
          break
        } else if (status.status === 'error') {
          setReportDistrict(null)
          window.alert(`Report generation failed: ${status.detail}`)
          break
        }
      }
    } catch (e) {
      window.alert(`Failed to generate report: ${e.message}`)
      setReportDistrict(null)
    } finally {
      setReportLoading(false)
    }
  }, [])

  const handleOpenClientReport = useCallback(async (district) => {
    if (district.client_report) {
      setClientReportDistrict(district)
      return
    }
    setClientReportLoading(true)
    setClientReportDistrict({ ...district, _generating: true })
    try {
      await api.generateTexasClientReport(district.district_id)
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const status = await api.getTexasClientReportStatus(district.district_id)
        if (status.status === 'done') {
          const fresh = await api.getTexasDistrict(district.district_id)
          setClientReportDistrict(fresh)
          setDistricts(prev => prev.map(d =>
            d.district_id === district.district_id ? fresh : d
          ))
          break
        } else if (status.status === 'error') {
          setClientReportDistrict(null)
          window.alert(`Client report generation failed: ${status.detail}`)
          break
        }
      }
    } catch (e) {
      window.alert(`Failed to generate client report: ${e.message}`)
      setClientReportDistrict(null)
    } finally {
      setClientReportLoading(false)
    }
  }, [])

  const visibleDistricts = filter === 'troubled'
    ? districts.filter(d => d.trouble_score >= 40)
    : districts

  const troubledCount = districts.filter(d => d.trouble_score >= 40).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--bg)' }}>

      {/* ── Header ── */}
      <div style={{
        padding: '20px 28px 16px', borderBottom: '1px solid var(--border)',
        background: 'var(--surface)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 18, fontFamily: 'var(--display)', fontWeight: 800, color: 'var(--navy)' }}>
                Texas District Screener
              </span>
              <Badge label="TEA TAPR" fg="#1A2158" bg="#EEF0FF" bd="#C7CBF0" />
              <Badge label="BABBAGE READY" fg="#166534" bg="#F0FDF4" bd="#BBF7D0" />
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--mono)' }}>
              Identify troubled Texas districts by ESC region — generate Babbage IEP/504 compliance sales reports
            </div>
          </div>
          {selectedRegion && districts.length > 0 && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: '#C8005A', fontFamily: 'var(--display)' }}>
                  {troubledCount}
                </div>
                <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  TROUBLED DISTRICTS
                </div>
              </div>
              <div style={{ width: 1, height: 36, background: 'var(--border)' }} />
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--navy)', fontFamily: 'var(--display)' }}>
                  {districts.length}
                </div>
                <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  TOTAL SCANNED
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>

        {/* ── Region selector ── */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 10, textTransform: 'uppercase' }}>
            Select ESC Region
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {ESC_REGIONS.map(r => (
              <button
                key={r}
                onClick={() => { setSelectedRegion(r); setScanStatus(null) }}
                style={{
                  padding: '7px 14px', borderRadius: 8, cursor: 'pointer',
                  background: selectedRegion === r ? 'var(--navy)' : 'var(--surface)',
                  color: selectedRegion === r ? '#fff' : 'var(--text-secondary)',
                  border: selectedRegion === r ? '1px solid var(--navy)' : '1px solid var(--border)',
                  fontSize: 11, fontFamily: 'var(--mono)', fontWeight: selectedRegion === r ? 700 : 400,
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ fontWeight: 700 }}>Region {r}</div>
                <div style={{ fontSize: 9, opacity: 0.7, marginTop: 1 }}>{REGION_CITIES[r]}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Scan controls ── */}
        {selectedRegion && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '14px 18px', borderRadius: 10,
            background: 'var(--surface)', border: '1px solid var(--border)',
            marginBottom: 20,
          }}>
            <button
              onClick={handleScan}
              disabled={scanning}
              style={{
                padding: '9px 22px', borderRadius: 8, border: 'none',
                background: scanning ? '#94A3B8' : 'var(--magenta)', color: '#fff',
                fontSize: 12, fontFamily: 'var(--display)', fontWeight: 700,
                cursor: scanning ? 'not-allowed' : 'pointer',
              }}
            >
              {scanning ? 'Scanning...' : `Scan Region ${selectedRegion}`}
            </button>

            {districts.length > 0 && !scanning && (
              <div style={{ display: 'flex', gap: 6 }}>
                {['troubled', 'all'].map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    style={{
                      padding: '6px 14px', borderRadius: 6, cursor: 'pointer',
                      background: filter === f ? '#1A2158' : 'transparent',
                      color: filter === f ? '#fff' : 'var(--text-muted)',
                      border: `1px solid ${filter === f ? '#1A2158' : 'var(--border)'}`,
                      fontSize: 11, fontFamily: 'var(--mono)',
                    }}
                  >
                    {f === 'troubled' ? `Troubled (${troubledCount})` : `All (${districts.length})`}
                  </button>
                ))}
              </div>
            )}

            {scanStatus && (
              <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: scanStatus.status === 'error' ? '#C8005A' : 'var(--text-muted)', flex: 1 }}>
                {scanning && (
                  <span style={{ marginRight: 8, display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
                )}
                {scanStatus.detail}
                {scanStatus.status === 'done' && scanStatus.troubled != null && (
                  <span style={{ marginLeft: 12, color: '#C8005A', fontWeight: 700 }}>
                    {scanStatus.troubled} troubled · {scanStatus.accounts_created} added to prospects
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Districts table ── */}
        {loading && (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--mono)', fontSize: 12 }}>
            Loading districts...
          </div>
        )}

        {!loading && visibleDistricts.length > 0 && (
          <div style={{ borderRadius: 10, border: '1px solid var(--border)', overflow: 'hidden' }}>
            {/* Table header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '2fr 90px 100px 90px 90px 90px 140px 120px 110px',
              gap: 0,
              background: 'var(--surface)',
              borderBottom: '1px solid var(--border)',
              padding: '9px 16px',
            }}>
              {['District', 'Enroll.', 'Rating', 'Score', 'STAAR Rd', 'STAAR Ma', 'Turns over', 'Pipeline', 'Report'].map(h => (
                <div key={h} style={{ fontSize: 9, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  {h}
                </div>
              ))}
            </div>

            {/* Table rows */}
            {visibleDistricts.map((d, i) => {
              const sc = scoreColor(d.trouble_score)
              const rc = ratingColor(d.accountability_rating)
              return (
                <div
                  key={d.district_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '2fr 90px 100px 90px 90px 90px 140px 120px 110px',
                    gap: 0,
                    padding: '10px 16px',
                    background: i % 2 === 0 ? 'var(--bg)' : 'var(--surface)',
                    borderBottom: '1px solid var(--border)',
                    alignItems: 'center',
                  }}
                >
                  {/* Name + flags */}
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--navy)', marginBottom: 2 }}>
                      {d.district_name}
                    </div>
                    {d.trouble_flags?.slice(0, 1).map((flag, fi) => (
                      <div key={fi} style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--mono)', lineHeight: 1.4 }}>
                        ↳ {flag.substring(0, 70)}{flag.length > 70 ? '…' : ''}
                      </div>
                    ))}
                  </div>

                  {/* Enrollment */}
                  <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                    {d.enrollment ? d.enrollment.toLocaleString() : '—'}
                  </div>

                  {/* Rating */}
                  <div>
                    <Badge
                      label={ratingLabel(d.accountability_rating)}
                      fg={rc.fg} bg={rc.bg} bd={rc.bd}
                    />
                  </div>

                  {/* Trouble Score */}
                  <div>
                    <span style={{
                      fontSize: 13, fontWeight: 800, color: sc.fg,
                      fontFamily: 'var(--display)',
                    }}>{d.trouble_score}</span>
                    <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginLeft: 2 }}>/100</span>
                  </div>

                  {/* STAAR Reading */}
                  <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: d.staar_reading_pct < 46 ? '#B45309' : 'var(--text-secondary)' }}>
                    {d.staar_reading_pct != null ? `${d.staar_reading_pct.toFixed(0)}%` : '—'}
                  </div>

                  {/* STAAR Math */}
                  <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: d.staar_math_pct < 44 ? '#B45309' : 'var(--text-secondary)' }}>
                    {d.staar_math_pct != null ? `${d.staar_math_pct.toFixed(0)}%` : '—'}
                  </div>

                  {/* Teacher turnover */}
                  <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: d.teacher_turnover_pct > 18 ? '#C8005A' : 'var(--text-secondary)' }}>
                    {d.teacher_turnover_pct != null ? `${d.teacher_turnover_pct.toFixed(0)}% turnover` : '—'}
                  </div>

                  {/* Pipeline button */}
                  <div>
                    {(d.account_id || pipelineIds.has(d.district_id)) ? (
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '3px 8px', borderRadius: 5,
                        background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0',
                        fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap',
                        display: 'inline-block',
                      }}>✓ In Pipeline</span>
                    ) : (
                      <button
                        onClick={() => handleAddToPipeline(d)}
                        disabled={pipelining === d.district_id}
                        style={{
                          padding: '5px 10px', borderRadius: 6, border: '1px solid #1A2158',
                          background: pipelining === d.district_id ? '#94A3B8' : '#1A2158',
                          color: '#fff', fontSize: 10, fontFamily: 'var(--display)', fontWeight: 700,
                          cursor: pipelining === d.district_id ? 'not-allowed' : 'pointer',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {pipelining === d.district_id ? '...' : '+ Pipeline'}
                      </button>
                    )}
                  </div>

                  {/* Report buttons — stacked */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {/* Internal sales report */}
                    <button
                      onClick={() => handleOpenReport(d)}
                      disabled={reportLoading && reportDistrict?.district_id === d.district_id}
                      style={{
                        padding: '4px 10px', borderRadius: 5, border: 'none',
                        background: d.babbage_pitch ? 'var(--navy)' : 'var(--magenta)',
                        color: '#fff', fontSize: 9, fontFamily: 'var(--display)', fontWeight: 700,
                        cursor: 'pointer', whiteSpace: 'nowrap',
                      }}
                    >
                      {reportLoading && reportDistrict?.district_id === d.district_id
                        ? 'Generating...'
                        : d.babbage_pitch ? 'Sales Intel ▸' : 'Build Intel'}
                    </button>
                    {/* Client-facing proposal */}
                    <button
                      onClick={() => handleOpenClientReport(d)}
                      disabled={clientReportLoading && clientReportDistrict?.district_id === d.district_id}
                      style={{
                        padding: '4px 10px', borderRadius: 5, border: 'none',
                        background: d.client_report ? 'var(--navy)' : 'var(--magenta)',
                        color: '#fff', fontSize: 9, fontFamily: 'var(--display)', fontWeight: 700,
                        cursor: 'pointer', whiteSpace: 'nowrap',
                        opacity: clientReportLoading && clientReportDistrict?.district_id === d.district_id ? 0.6 : 1,
                      }}
                    >
                      {clientReportLoading && clientReportDistrict?.district_id === d.district_id
                        ? 'Generating...'
                        : d.client_report ? 'Client Report ▸' : 'Client Report'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Empty states */}
        {!loading && selectedRegion && districts.length === 0 && !scanning && !scanStatus && (
          <div style={{
            textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)',
            fontFamily: 'var(--mono)', fontSize: 12,
          }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>🤠</div>
            <div style={{ fontWeight: 700, color: 'var(--navy)', marginBottom: 6 }}>Region {selectedRegion} not yet scanned</div>
            <div>Click "Scan Region {selectedRegion}" to fetch TEA TAPR performance data</div>
            <div style={{ marginTop: 4, fontSize: 10, color: 'var(--text-faint)' }}>
              Fetches district list and performance metrics from Texas Education Agency
            </div>
          </div>
        )}

        {!loading && selectedRegion && filter === 'troubled' && visibleDistricts.length === 0 && districts.length > 0 && (
          <div style={{
            textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)',
            fontFamily: 'var(--mono)', fontSize: 12,
          }}>
            <div style={{ fontSize: 28, marginBottom: 12 }}>✓</div>
            <div style={{ fontWeight: 700, color: '#166534', marginBottom: 6 }}>No troubled districts found</div>
            <div>All {districts.length} districts in Region {selectedRegion} scored below the threshold (40).</div>
            <button onClick={() => setFilter('all')} style={{
              marginTop: 12, padding: '7px 16px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text-secondary)', fontSize: 11,
              fontFamily: 'var(--mono)', cursor: 'pointer',
            }}>View all districts →</button>
          </div>
        )}

        {!selectedRegion && (
          <div style={{
            textAlign: 'center', padding: '64px 0', color: 'var(--text-muted)',
            fontFamily: 'var(--mono)', fontSize: 12,
          }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🗺</div>
            <div style={{ fontWeight: 700, color: 'var(--navy)', marginBottom: 6, fontSize: 14 }}>
              Select an ESC Region to begin
            </div>
            <div>Texas has 20 Education Service Center regions. Select one above to screen districts for Babbage opportunities.</div>
          </div>
        )}
      </div>

      {/* ── Internal Sales Report Modal ── */}
      {reportDistrict && (
        <TexasReportModal
          isOpen={!!reportDistrict}
          district={reportDistrict}
          loading={reportDistrict._generating}
          onClose={() => setReportDistrict(null)}
        />
      )}

      {/* ── Client Report Modal ── */}
      {clientReportDistrict && (
        <TexasClientReportModal
          isOpen={!!clientReportDistrict}
          district={clientReportDistrict}
          loading={clientReportDistrict._generating}
          onClose={() => setClientReportDistrict(null)}
        />
      )}
    </div>
  )
}
