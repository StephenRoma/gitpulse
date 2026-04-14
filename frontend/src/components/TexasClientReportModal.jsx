import { Spinner } from '@blueprintjs/core'
import logoUrl from '../assets/logo.svg'

function urgBadge(urgency) {
  const map = {
    high:   { bg: '#C8005A', label: 'HIGH PRIORITY' },
    medium: { bg: '#D97706', label: 'MED PRIORITY' },
    low:    { bg: '#2563EB', label: 'LOW PRIORITY' },
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

export default function TexasClientReportModal({ isOpen, onClose, district, loading }) {
  if (!isOpen) return null

  const report = district?.client_report || {}
  const name   = district?.district_name || 'Unknown District'

  async function handleDownload() {
    const printEl = document.getElementById('tx-client-report-body')
    if (!printEl) return

    // Fetch and base64-encode the SVG logo so it works in a print popup window
    let logoDataUri = ''
    try {
      const resp = await fetch(logoUrl)
      const blob = await resp.blob()
      logoDataUri = await new Promise((resolve) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result)
        reader.readAsDataURL(blob)
      })
    } catch (_) {
      // logo won't appear in print but report still works
    }

    const html = printEl.innerHTML
    const win = window.open('', '_blank', 'width=960,height=860')
    win.document.write(`<!DOCTYPE html><html><head>
      <title>Babbage Proposal — ${name}</title>
      <meta charset="utf-8" />
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @page { size: A4; margin: 20mm 18mm; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          font-size: 12px; color: #1A2158; background: #fff; line-height: 1.5;
        }
        .report-page { max-width: 760px; margin: 0 auto; }
        .section { page-break-inside: avoid; break-inside: avoid; margin-bottom: 28px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB; }
        .section:last-child { border-bottom: none; }
        h1 { font-size: 22px; font-weight: 800; color: #1A2158; }
        h2 { font-size: 13px; font-weight: 700; color: #1A2158; margin-bottom: 10px; }
        .section-mono { font-size: 9px; font-family: monospace; font-weight: 700; letter-spacing: 0.1em; color: #B0BCDA; margin-bottom: 10px; text-transform: uppercase; }
        .card { border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; background: #F8F9FF; }
        .challenge-row { padding: 8px 14px; border-radius: 7px; margin-bottom: 8px; background: #FFF7ED; border: 1px solid #FED7AA; }
        .outcome-row { display: flex; gap: 10px; padding: 8px 14px; border-radius: 7px; margin-bottom: 8px; background: #F0FDF4; border: 1px solid #BBF7D0; }
        .cta-box { padding: 16px 20px; background: #EEF0FF; border-radius: 10px; border: 1px solid #C7CBF0; font-size: 13px; font-weight: 500; color: #1A2158; }
        .logo-header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 18px; margin-bottom: 22px; border-bottom: 2px solid #1A2158; }
        img.babbage-logo { height: 72px; width: auto; }
        .footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #E5E7EB; display: flex; justify-content: space-between; }
        .footer span { font-size: 9px; font-family: monospace; color: #B0BCDA; }
      </style>
    </head><body><div class="report-page">
      <div class="logo-header">
        ${logoDataUri ? `<img class="babbage-logo" src="${logoDataUri}" alt="Babbage" />` : '<div style="font-family:monospace;font-weight:800;font-size:18px;color:#1A2158">BABBAGE</div>'}
        <div style="text-align:right">
          <div style="font-size:9px;font-family:monospace;color:#B0BCDA;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Client Proposal</div>
          <div style="font-size:18px;font-weight:800;color:#1A2158">${name}</div>
        </div>
      </div>
      ${html}
      <div class="footer">
        <span>BABBAGE · IEP/504 ACCOMMODATION COMPLIANCE PLATFORM</span>
        <span>${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </div></body></html>`)
    win.document.close()
    setTimeout(() => { win.focus(); win.print() }, 600)
  }

  return (
    <>
      {/* Overlay */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 1001,
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
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '16px 28px', borderBottom: '1px solid #E5E7EB',
            background: '#F8F9FF', gap: 20,
          }}>
            {/* Babbage logo — standalone left column, never squeezed */}
            <img
              src={logoUrl}
              alt="Babbage"
              style={{ height: 90, width: 'auto', display: 'block', flexShrink: 0 }}
            />

            {/* District info — grows to fill remaining space */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 18, color: '#1A2158' }}>
                  {name}
                </span>
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4,
                  background: '#EEF0FF', color: '#1A2158', border: '1px solid #C7CBF0',
                  fontFamily: 'var(--mono)', letterSpacing: '0.06em',
                }}>CLIENT PROPOSAL</span>
              </div>
              <div style={{ display: 'flex', gap: 10, fontSize: 11, fontFamily: 'var(--mono)', color: '#6B7280', flexWrap: 'wrap' }}>
                <span>ESC Region {district?.esc_region}</span>
                <span>·</span>
                <span>{district?.enrollment ? district.enrollment.toLocaleString() + ' students' : 'Enrollment unknown'}</span>
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
              {!loading && report.tagline && (
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
                <div style={{ fontWeight: 700, color: '#1A2158' }}>Generating Client Proposal</div>
                <div style={{ fontSize: 11 }}>Claude is writing a proposal tailored to this district...</div>
              </div>
            ) : !report.tagline ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: '#6B7280', fontFamily: 'var(--mono)' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1A2158', marginBottom: 8 }}>No proposal generated yet</div>
                <div>Close this dialog and click "Client Report" to generate the proposal.</div>
              </div>
            ) : (
              <div id="tx-client-report-body">

                {/* ── Tagline + About Babbage ── */}
                <div style={{ marginBottom: 28 }}>
                  <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 8, textTransform: 'uppercase' }}>
                    About Babbage
                  </div>
                  {report.tagline && (
                    <p style={{ fontSize: 15, fontWeight: 700, color: '#1A2158', lineHeight: 1.5, marginBottom: 10 }}>
                      {report.tagline}
                    </p>
                  )}
                  {report.what_we_do && (
                    <p style={{ fontSize: 13, lineHeight: 1.7, color: '#374151' }}>
                      {report.what_we_do}
                    </p>
                  )}
                </div>

                {/* ── What We Noticed ── */}
                {(report.district_context || report.challenges_identified?.length > 0) && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 8, textTransform: 'uppercase' }}>
                      What We Noticed About {name}
                    </div>
                    {report.district_context && (
                      <p style={{ fontSize: 13, lineHeight: 1.65, color: '#374151', marginBottom: 12 }}>
                        {report.district_context}
                      </p>
                    )}
                    {report.challenges_identified?.map((c, i) => (
                      <div key={i} style={{
                        padding: '10px 14px', borderRadius: 8, marginBottom: 8,
                        background: '#FFF7ED', border: '1px solid #FED7AA',
                      }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#92400E', marginBottom: 3 }}>{c.challenge}</div>
                        <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.5 }}>{c.context}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── How Babbage Can Help ── */}
                {report.how_we_help?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      How Babbage Can Help
                    </div>
                    {report.how_we_help.map((h, i) => (
                      <div key={i} style={{
                        border: '1px solid #E5E7EB', borderRadius: 10, padding: '12px 16px',
                        marginBottom: 10, background: '#F8F9FF',
                      }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#1A2158', marginBottom: 4 }}>{h.capability}</div>
                        <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.5 }}>{h.benefit}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── Expected Outcomes ── */}
                {report.expected_outcomes?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 10, textTransform: 'uppercase' }}>
                      Expected Outcomes
                    </div>
                    {report.expected_outcomes.map((o, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '10px 14px', borderRadius: 8, marginBottom: 8,
                        background: '#F0FDF4', border: '1px solid #BBF7D0',
                      }}>
                        <span style={{
                          fontSize: 14, lineHeight: 1, color: '#166534', flexShrink: 0, marginTop: 1,
                        }}>✓</span>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#15803D', marginBottom: 2 }}>{o.outcome}</div>
                          {o.detail && <div style={{ fontSize: 11, color: '#374151', lineHeight: 1.5 }}>{o.detail}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── Call to Action ── */}
                {report.call_to_action && (
                  <div style={{
                    padding: '18px 22px', background: '#EEF0FF', borderRadius: 12,
                    border: '1px solid #C7CBF0',
                  }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em', color: '#B0BCDA', marginBottom: 8, textTransform: 'uppercase' }}>
                      Let's Talk
                    </div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: '#1A2158', lineHeight: 1.65 }}>
                      {report.call_to_action}
                    </p>
                  </div>
                )}

              </div>
            )}
          </div>

        </div>
      </div>
    </>
  )
}
