import { Spinner } from '@blueprintjs/core'

const THEME_COLORS = {
  modernization:   '#7C3AED',
  cloud_migration: '#0369A1',
  ai_adoption:     '#0891B2',
  security:        '#C8005A',
  platform_eng:    '#1A2158',
  vendor_eval:     '#D97706',
  tech_debt:       '#B85042',
  performance:     '#2D6A4F',
  devex:           '#374060',
}

const SIGNAL_TYPE_LABELS = {
  star:          'Starred',
  fork:          'Forked',
  new_repo:      'New Repo',
  push:          'Pushed to',
  issue_comment: 'Issue Comment',
  release:       'Release',
  org_issue:     'Org Issue',
  hn_mention:    'HN Mention',
}

function confBadge(confidence) {
  const map = {
    high:   { bg: '#C8005A', label: 'HIGH' },
    medium: { bg: '#D97706', label: 'MED' },
    low:    { bg: '#2563EB', label: 'LOW' },
  }
  const c = map[confidence] || map.low
  return (
    <span style={{
      fontSize: 8, fontWeight: 700, padding: '2px 5px', borderRadius: 3,
      background: c.bg, color: '#fff', fontFamily: 'var(--mono)',
      letterSpacing: '0.06em', marginRight: 6, whiteSpace: 'nowrap', flexShrink: 0,
    }}>{c.label}</span>
  )
}

export default function ReportModal({ isOpen, onClose, report, loading, account }) {
  if (!isOpen) return null

  const generatedDate = report?.generated_at
    ? new Date(report.generated_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  const briefing  = report?.briefing || {}
  const themes    = report?.themes   || []
  const acctData  = report?.account  || account || {}
  const score     = acctData.signal_score ?? account?.signal_score ?? 0

  return (
    <>
      {/* Print styles injected into head via style tag */}
      <style>{`
        @media print {
          body > * { display: none !important; }
          #gp-report-print-root { display: block !important; position: static !important; }
          #gp-report-print-root .report-controls { display: none !important; }
          #gp-report-print-root .report-body { overflow: visible !important; max-height: none !important; }
          .theme-section { page-break-inside: avoid; }
        }
      `}</style>

      {/* Overlay */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(26,33,88,0.55)', backdropFilter: 'blur(3px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        padding: '32px 16px', overflowY: 'auto',
      }}>
        <div id="gp-report-print-root" style={{
          background: '#fff', borderRadius: 12, width: '100%', maxWidth: 820,
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Controls bar (hidden in print) */}
          <div className="report-controls" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '14px 20px', borderBottom: '1px solid #E5E7EB',
          }}>
            <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.08em' }}>
              ACCOUNT INTELLIGENCE REPORT
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => window.print()}
                disabled={loading}
                style={{
                  padding: '6px 16px', borderRadius: 7, border: 'none',
                  background: 'var(--navy)', color: '#fff',
                  fontSize: 11, fontFamily: 'var(--mono)', cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.5 : 1,
                }}
              >Download PDF</button>
              <button
                onClick={onClose}
                style={{
                  padding: '6px 14px', borderRadius: 7,
                  border: '1px solid var(--border)', background: 'transparent',
                  color: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--mono)', cursor: 'pointer',
                }}
              >Close</button>
            </div>
          </div>

          {/* Report body */}
          <div className="report-body" style={{ padding: '36px 44px', overflowY: 'auto', maxHeight: 'calc(100vh - 120px)' }}>

            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: '60px 0', color: 'var(--text-muted)' }}>
                <Spinner size={32} />
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>Claude is writing your report...</span>
              </div>
            ) : (
              <>
                {/* ── Header ─────────────────────────────────────────────── */}
                <div style={{ borderBottom: '2px solid var(--navy)', paddingBottom: 18, marginBottom: 24 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', letterSpacing: '0.12em', marginBottom: 6 }}>
                        CONFIDENTIAL · RELEVANTZ SALES INTELLIGENCE
                      </div>
                      <h1 style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 26, color: 'var(--navy)', margin: 0 }}>
                        {acctData.name || account?.name}
                      </h1>
                      <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                        {acctData.github_org && (
                          <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>
                            github.com/{acctData.github_org}
                          </span>
                        )}
                        <span style={{
                          fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 600,
                          padding: '1px 7px', borderRadius: 4,
                          background: acctData.account_type === 'client' ? '#F0FDF4' : '#EFF6FF',
                          color: acctData.account_type === 'client' ? '#166534' : '#1A6B9A',
                          border: `1px solid ${acctData.account_type === 'client' ? '#BBF7D0' : '#BFDBFE'}`,
                        }}>{acctData.account_type === 'client' ? 'Active Client' : 'Pipeline'}</span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', marginBottom: 4 }}>SIGNAL SCORE</div>
                      <div style={{
                        fontSize: 28, fontWeight: 800, fontFamily: 'var(--display)',
                        color: score >= 85 ? '#C8005A' : score >= 60 ? '#D97706' : '#2563EB',
                      }}>{score}<span style={{ fontSize: 12, color: '#B0BCDA' }}>/100</span></div>
                      <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', marginTop: 2 }}>
                        {generatedDate}
                      </div>
                    </div>
                  </div>
                </div>

                {/* ── AI Briefing ─────────────────────────────────────────── */}
                {briefing.summary && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em',
                      color: '#B0BCDA', marginBottom: 10 }}>EXECUTIVE BRIEFING</div>
                    <p style={{ fontSize: 13, lineHeight: 1.7, color: '#1A2158', margin: '0 0 12px' }}>
                      {briefing.summary}
                    </p>
                    {briefing.key_themes?.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                        {briefing.key_themes.map((t, i) => (
                          <span key={i} style={{
                            fontSize: 10, padding: '3px 10px', borderRadius: 20,
                            background: '#EFF1F8', color: 'var(--navy)',
                            fontFamily: 'var(--mono)', fontWeight: 500,
                          }}>{t}</span>
                        ))}
                      </div>
                    )}
                    {briefing.recommended_action && (
                      <div style={{ padding: '10px 14px', borderRadius: 7, background: '#FFF0F5',
                        border: '1px solid #FBCFE8', fontSize: 12, color: '#5A0028', lineHeight: 1.5 }}>
                        <strong style={{ fontSize: 9, fontFamily: 'var(--mono)', letterSpacing: '0.08em' }}>RECOMMENDED ACTION: </strong>
                        {briefing.recommended_action}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Prescient Calls ─────────────────────────────────────── */}
                {briefing.prescient_calls?.length > 0 && (
                  <div style={{ marginBottom: 28 }}>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em',
                      color: '#B0BCDA', marginBottom: 10 }}>PRESCIENT CALLS</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {briefing.prescient_calls.map((pc, i) => (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 12px',
                          borderRadius: 7, border: '1px solid #E5E7EB', background: '#FAFAFA',
                        }}>
                          {confBadge(pc.confidence)}
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--navy)', lineHeight: 1.4 }}>{pc.call}</div>
                            {pc.evidence && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.4 }}>{pc.evidence}</div>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── Theme Case Narratives ───────────────────────────────── */}
                {themes.length > 0 ? (
                  <div>
                    <div style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.1em',
                      color: '#B0BCDA', marginBottom: 14 }}>STRATEGIC CASE ANALYSIS</div>
                    {themes.map((t, i) => {
                      const themeColor = THEME_COLORS[t.theme] || '#1A2158'
                      return (
                        <div key={i} className="theme-section" style={{
                          marginBottom: 28, paddingBottom: 24,
                          borderBottom: i < themes.length - 1 ? '1px solid #E5E7EB' : 'none',
                        }}>
                          {/* Theme header */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                            <div style={{ width: 4, height: 24, borderRadius: 2, background: themeColor, flexShrink: 0 }} />
                            <h2 style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 15,
                              color: themeColor, margin: 0 }}>{t.label}</h2>
                            <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: '#B0BCDA', marginLeft: 'auto' }}>
                              {t.signals?.length || 0} signals
                            </span>
                          </div>

                          {/* Narrative */}
                          {t.narrative && (
                            <p style={{ fontSize: 13, lineHeight: 1.7, color: '#374151', margin: '0 0 14px',
                              paddingLeft: 14, borderLeft: `3px solid ${themeColor}30` }}>
                              {t.narrative}
                            </p>
                          )}

                          {/* Supporting signals evidence */}
                          {t.signals?.length > 0 && (
                            <div>
                              <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA',
                                letterSpacing: '0.08em', marginBottom: 7 }}>SUPPORTING EVIDENCE</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                                {t.signals.slice(0, 10).map((sig, j) => {
                                  const raw = typeof sig.raw_data === 'string'
                                    ? (() => { try { return JSON.parse(sig.raw_data) } catch { return {} } })()
                                    : (sig.raw_data || {})
                                  const typeLabel = SIGNAL_TYPE_LABELS[sig.signal_type] || sig.signal_type
                                  const desc = (raw.issue_title || sig.repo_description || '').slice(0, 90)
                                  return (
                                    <div key={j} style={{
                                      display: 'flex', alignItems: 'flex-start', gap: 8,
                                      padding: '6px 10px', borderRadius: 6,
                                      background: `${themeColor}08`, border: `1px solid ${themeColor}20`,
                                      fontSize: 11,
                                    }}>
                                      <span style={{
                                        fontSize: 8, padding: '2px 5px', borderRadius: 3, whiteSpace: 'nowrap',
                                        background: themeColor, color: '#fff', fontFamily: 'var(--mono)', flexShrink: 0,
                                        marginTop: 1,
                                      }}>{typeLabel.toUpperCase()}</span>
                                      <div style={{ flex: 1, minWidth: 0 }}>
                                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--navy)' }}>@{sig.engineer_username}</span>
                                        <span style={{ color: 'var(--text-faint)', margin: '0 4px' }}>→</span>
                                        <span style={{ color: '#1A6B9A', fontFamily: 'var(--mono)' }}>{sig.repo_name}</span>
                                        {desc && <span style={{ color: 'var(--text-secondary)', marginLeft: 6 }}>{desc}</span>}
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: 13, fontFamily: 'var(--mono)' }}>
                    No tagged signals found. Tag signals in the feed with strategic themes, then regenerate.
                  </div>
                )}

                {/* ── Footer ─────────────────────────────────────────────── */}
                <div style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #E5E7EB',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA', letterSpacing: '0.08em' }}>
                    GENERATED BY GITPULSE · RELEVANTZ SALES INTELLIGENCE
                  </span>
                  <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: '#B0BCDA' }}>{generatedDate}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
