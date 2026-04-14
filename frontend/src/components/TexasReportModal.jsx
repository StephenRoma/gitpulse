import { Spinner } from '@blueprintjs/core'

const SEVERITY_STYLES = {
  critical: { fg: '#B91C1C', bg: '#FEF2F2', bd: '#FECACA', label: 'CRITICAL' },
  high:     { fg: '#B45309', bg: '#FFFBEB', bd: '#FDE68A', label: 'HIGH' },
  medium:   { fg: '#0369A1', bg: '#EFF6FF', bd: '#BFDBFE', label: 'MEDIUM' },
}

function sevBadge(severity) {
  const s = SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium
  return (
    <span style={{
      fontSize: 8, fontWeight: 700, padding: '2px 5px', borderRadius: 3,
      background: s.bg, color: s.fg, border: `1px solid ${s.bd}`,
      fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap',
      flexShrink: 0,
    }}>{s.label}</span>
  )
}

function urgBadge(urgency) {
  const map = {
    high:   { bg: '#C8005A', label: 'HIGH URGENCY' },
    medium: { bg: '#D97706', label: 'MED URGENCY' },
    low:    { bg: '#2563EB', label: 'LOW URGENCY' },
  }
  const c = map[urgency] || map.medium
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
      background: c.bg, color: '#fff', fontFamily: 'var(--mono)',
      letterSpacing: '0.06em',
    }}>{c.label}</span>
  )
}

function ratingLabel(rating) {
  if (!rating) return 'Unrated'
  if (rating === 'IR') return 'Improvement Required'
  if (rating === 'NR') return 'Not Rated'
  return `Rating ${rating}`
}

export default function TexasReportModal({ isOpen, onClose, district, loading }) {
  if (!isOpen) return null

  const pitch = district?.babbage_pitch || {}
  const name  = district?.district_name || 'Unknown District'

  function handleDownload() {
    const printEl = document.getElementById('tx-report-body')
    if (!printEl) return
    const html = printEl.innerHTML
    const win = window.open('', '_blank', 'width=960,height=860')
    win.document.write(`<!DOCTYPE html><html><head>
      <title>Babbage Sales Report — ${name}</title>
      <meta charset="utf-8" />
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @page { size: A4; margin: 20mm 18mm; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          font-size: 12px; color: #1A2158; background: #fff; line-height: 1.5;
        }
        .report-page { max-width: 760px; margin: 0 auto; }
        .page-break { page-break-after: always; break-after: always; }
        .section { page-break-inside: avoid; break-inside: avoid; margin-bottom: 28px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB; }
        .section:last-child { border-bottom: none; }
        h1 { font-size: 24px; font-weight: 800; color: #1A2158; }
        h2 { font-size: 13px; font-weight: 700; color: #1A2158; margin-bottom: 10px; }
        .badge { display: inline-block; font-size: 8px; font-weight: 700; padding: 2px 5px; border-radius: 3px; font-family: monospace; letter-spacing: 0.06em; white-space: nowrap; }
        .row { display: flex; align-items: flex-start; gap: 8px; padding: 7px 12px; border-radius: 6px; margin-bottom: 6px; }
        .section-mono { font-size: 9px; font-family: monospace; font-weight: 700; letter-spacing: 0.1em; color: #B0BCDA; margin-bottom: 10px; text-transform: uppercase; }
        .solution-card { border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
        .kpi-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        .kpi-table th { background: #EEF0FF; color: #1A2158; font-weight: 700; padding: 7px 10px; text-align: left; }
        .kpi-table td { padding: 7px 10px; border-bottom: 1px solid #F3F4F6; }
        .talking-point { padding: 8px 12px 8px 16px; border-left: 3px solid #C8005A; margin-bottom: 8px; background: #FFF0F5; border-radius: 0 6px 6px 0; font-size: 11px; }
        .footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #E5E7EB; display: flex; justify-content: space-between; }
        .footer span { font-size: 9px; font-family: monospace; color: #B0BCDA; }
      </style>
    </head><body><div class="report-page">${html}</div></body></html>`)
    win.document.close()
    setTimeout(() => { win.focus(); win.print() }, 600)
  }

  return (
    <>
      {/* Overlay */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(26,33,88,0.55)', backdropFilter: 'blur(3px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        padding: '32px 16px', overflowY: 'auto',
      }} onClick={onClose}>
        <div style={{
          background: '#fff', borderRadius: 16, maxWidth: 860, width: '100%',
          boxShadow: '0 24px 64px rgba(26,33,88,0.3)', overflow: 'hidden',
          position: 'relative',
        }} onClick={e => e.stopPropagation()}>

          {/* Modal header */}
          <div style={{
            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
            padding: '22px 28px 18px', borderBottom: '1px solid #E5E7EB',
            background: '#F8F9FF',
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <span style={{
                  fontFamily: 'var(--display)', fontWeight: 800, fontSize: 20, color: '#1A2158'
                }}>{name}</span>
                {district?.trouble_score >= 60 && (
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4,
                    background: '#FFF0F5', color: '#C8005A', border: '1px solid #FBCFE8',
                    fontFamily: 'var(--mono)', letterSpacing: '0.06em',
                  }}>HIGH OPPORTUNITY</span>
                )}
                {pitch.urgency && urgBadge(pitch.urgency)}
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 11, fontFamily: 'var(--mono)', color: '#6B7280' }}>
                <span>ESC Region {district?.esc_region}</span>
                <span>·</span>
                <span>{district?.enrollment ? district.enrollment.toLocaleString() + ' students' : 'Enrollment unknown'}</span>
                <span>·</span>
                <span>{ratingLabel(district?.accountability_rating)}</span>
                <span>·</span>
                <span>Trouble Score: <strong style={{ color: '#C8005A' }}>{district?.trouble_score}/100</strong></span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {!loading && pitch.executive_summary && (
                <button onClick={handleDownload} style={{
                  padding: '8px 16px', borderRadius: 8,
                  border: '1px solid #C7CBF0', background: '#EEF0FF',
                  color: '#1A2158', fontSize: 11, fontFamily: 'var(--mono)',
                  fontWeight: 700, cursor: 'pointer',
                }}>⬇ Print / PDF</button>
              )}
              <button onClick={onClose} style={{
                padding: '8px 14px', borderRadius: 8, border: '1px solid #E5E7EB',
                background: '#fff', color: '#6B7280', fontSize: 18, cursor: 'pointer',
                lineHeight: 1,
              }}>×</button>
            </div>
          </div>

          {/* Modal body */}
          <div style={{ padding: '24px 28px', overflowY: 'auto', maxHeight: 'calc(90vh - 140px)' }}>
            {loading ? (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                gap: 16, padding: '64px 0', color: '#6B7280', fontFamily: 'var(--mono)',
              }}>
                <Spinner size={32} />
                <div style={{ fontWeight: 700, color: '#1A2158' }}>Generating Babbage Sales Report</div>
                <div style={{ fontSize: 11 }}>Claude is analyzing district data and writing your pitch...</div>
              </div>
            ) : !pitch.executive_summary ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: '#6B7280', fontFamily: 'var(--mono)' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1A2158', marginBottom: 8 }}>No report generated yet</div>
                <div>Close this dialog and click "Build Report" to generate the Babbage sales pitch.</div>
              </div>
            ) : (
              <div id="tx-report-body">

                {/* ── Report header (for print) ── */}
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                  paddingBottom: 20, marginBottom: 24, borderBottom: '2px solid #1A2158',
                }}>
                  <div>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>
                      Babbage Sales Intelligence Report
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#1A2158', fontFamily: 'var(--display)' }}>
                      {name}
                    </div>
                    <div style={{ fontSize: 11, color: '#6B7280', marginTop: 4, fontFamily: 'var(--mono)' }}>
                      ESC Region {district?.esc_region} · {district?.enrollment?.toLocaleString() ?? '?'} students · {ratingLabel(district?.accountability_rating)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 32, fontWeight: 900, color: '#C8005A', fontFamily: 'var(--display)' }}>
                      {district?.trouble_score}
                    </div>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', letterSpacing: '0.08em' }}>
                      TROUBLE SCORE / 100
                    </div>
                  </div>
                </div>

                {/* ── Executive Summary ── */}
                <div style={{ marginBottom: 28 }}>
                  <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 8, textTransform: 'uppercase' }}>
                    Executive Summary
                  </div>
                  <p style={{ fontSize: 13, lineHeight: 1.65, color: '#1A2158', fontWeight: 500 }}>
                    {pitch.executive_summary}
                  </p>
                </div>

                {/* ── District Failures ── */}
                {pitch.district_failures?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      District Performance Failures
                    </div>
                    {pitch.district_failures.map((f, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '9px 14px', borderRadius: 8, marginBottom: 6,
                        background: f.severity === 'critical' ? '#FEF2F2' : f.severity === 'high' ? '#FFFBEB' : '#F8FAFC',
                        border: `1px solid ${f.severity === 'critical' ? '#FECACA' : f.severity === 'high' ? '#FDE68A' : '#E5E7EB'}`,
                      }}>
                        {sevBadge(f.severity)}
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#1A2158' }}>{f.metric}</div>
                          <div style={{ fontSize: 11, color: '#374151', marginTop: 2 }}>{f.value}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── Babbage Solutions ── */}
                {pitch.babbage_solutions?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      How Babbage Addresses These Gaps
                    </div>
                    {pitch.babbage_solutions.map((s, i) => (
                      <div key={i} style={{
                        border: '1px solid #E5E7EB', borderRadius: 10, padding: '14px 16px',
                        marginBottom: 10, background: '#F8F9FF',
                      }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                          <span style={{
                            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                            background: '#FEF2F2', color: '#B91C1C', border: '1px solid #FECACA',
                            fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap', flexShrink: 0,
                          }}>PROBLEM</span>
                          <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.5 }}>{s.problem}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                          <span style={{
                            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                            background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0',
                            fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap', flexShrink: 0,
                          }}>SOLUTION</span>
                          <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.5 }}>{s.solution}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                          <span style={{
                            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                            background: '#EEF0FF', color: '#1A2158', border: '1px solid #C7CBF0',
                            fontFamily: 'var(--mono)', letterSpacing: '0.06em', whiteSpace: 'nowrap', flexShrink: 0,
                          }}>KPI TARGET</span>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#1A2158', lineHeight: 1.5 }}>{s.kpi_target}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── KPI Projections ── */}
                {pitch.kpi_projections?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      KPI Projections
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead>
                        <tr style={{ background: '#EEF0FF' }}>
                          {['KPI', 'Current State', 'Target', 'Timeframe'].map(h => (
                            <th key={h} style={{
                              textAlign: 'left', padding: '8px 12px', fontWeight: 700,
                              fontSize: 10, fontFamily: 'var(--mono)', color: '#1A2158',
                              letterSpacing: '0.05em', textTransform: 'uppercase',
                            }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {pitch.kpi_projections.map((k, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #F3F4F6', background: i % 2 === 0 ? '#fff' : '#FAFAF9' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600, color: '#1A2158' }}>{k.kpi}</td>
                            <td style={{ padding: '8px 12px', color: '#B45309', fontFamily: 'var(--mono)' }}>{k.current}</td>
                            <td style={{ padding: '8px 12px', color: '#166534', fontWeight: 700, fontFamily: 'var(--mono)' }}>{k.target}</td>
                            <td style={{ padding: '8px 12px', color: '#6B7280', fontFamily: 'var(--mono)' }}>{k.timeframe}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* ── Talking Points ── */}
                {pitch.opening_talking_points?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      Opening Talking Points for Sales Team
                    </div>
                    {pitch.opening_talking_points.map((tp, i) => (
                      <div key={i} style={{
                        padding: '10px 14px 10px 18px',
                        borderLeft: '3px solid #C8005A',
                        background: '#FFF0F5',
                        borderRadius: '0 8px 8px 0',
                        marginBottom: 8,
                      }}>
                        <div style={{ fontSize: 11, color: '#1A2158', lineHeight: 1.6 }}>
                          <span style={{ fontWeight: 700, color: '#C8005A', marginRight: 8 }}>{i + 1}.</span>
                          {tp}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── Report footer (for print) ── */}
                <div style={{
                  marginTop: 24, paddingTop: 16, borderTop: '1px solid #E5E7EB',
                  display: 'flex', justifyContent: 'space-between',
                }}>
                  <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA' }}>
                    Babbage IEP/504 Compliance Platform · Sales Intelligence Report
                  </span>
                  <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA' }}>
                    Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                  </span>
                </div>

              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
