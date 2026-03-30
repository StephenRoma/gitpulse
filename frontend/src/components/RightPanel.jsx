import { useState, useEffect, useRef } from 'react'
import { Spinner } from '@blueprintjs/core'
import { api } from '../api'

const PALETTE = ['#C8005A','#1A6B9A','#2D6A4F','#6D3A9C','#B85042','#D97706','#0369A1','#374060']

function sigHeat(signal) {
  try {
    const score = JSON.parse(signal.raw_data || '{}').sig_score || 0
    return score >= 6 ? 'hot' : score >= 3 ? 'warm' : 'cool'
  } catch { return 'cool' }
}
function heatFg(h) { return h === 'hot' ? '#C8005A' : h === 'warm' ? '#D97706' : '#2563EB' }
function heatBg(h) { return h === 'hot' ? '#FFF0F5' : h === 'warm' ? '#FFFBEB' : '#EFF6FF' }
function heatBd(h) { return h === 'hot' ? '#FBCFE8' : h === 'warm' ? '#FDE68A' : '#BFDBFE' }

const WELCOME = 'Ask me anything about this account\u2019s signals, engineers, tech stack, or next steps \u2014 I have full context.'

// Render markdown-ish text without a library
function MsgContent({ text }) {
  const lines = text.split('\n')
  const nodes = []
  let key = 0
  for (const raw of lines) {
    const line = raw
    // H3 ### or H2 ##
    if (/^###\s+/.test(line)) {
      nodes.push(<div key={key++} style={{ fontWeight: 700, fontSize: 11, color: 'var(--navy)', marginTop: 8, marginBottom: 2, fontFamily: 'var(--display)', letterSpacing: '0.02em' }}>{line.replace(/^###\s+/, '')}</div>)
    } else if (/^##\s+/.test(line)) {
      nodes.push(<div key={key++} style={{ fontWeight: 800, fontSize: 12, color: 'var(--navy)', marginTop: 10, marginBottom: 3, fontFamily: 'var(--display)' }}>{line.replace(/^##\s+/, '')}</div>)
    } else if (/^\*\*(.+)\*\*$/.test(line.trim())) {
      // Standalone bold line = section header
      nodes.push(<div key={key++} style={{ fontWeight: 700, fontSize: 11, color: 'var(--navy)', marginTop: 8, marginBottom: 2, fontFamily: 'var(--display)' }}>{line.trim().replace(/^\*\*|\*\*$/g, '')}</div>)
    } else if (/^[-*]\s+/.test(line)) {
      // Bullet
      const content = line.replace(/^[-*]\s+/, '')
      nodes.push(
        <div key={key++} style={{ display: 'flex', gap: 6, marginBottom: 2 }}>
          <span style={{ color: 'var(--magenta)', flexShrink: 0, marginTop: 1 }}>&#x2022;</span>
          <span>{renderInline(content)}</span>
        </div>
      )
    } else if (/^\d+\.\s+/.test(line)) {
      // Numbered list
      const num = line.match(/^(\d+)\./)[1]
      const content = line.replace(/^\d+\.\s+/, '')
      nodes.push(
        <div key={key++} style={{ display: 'flex', gap: 6, marginBottom: 2 }}>
          <span style={{ color: 'var(--magenta)', flexShrink: 0, fontWeight: 600, minWidth: 14 }}>{num}.</span>
          <span>{renderInline(content)}</span>
        </div>
      )
    } else if (line.trim() === '') {
      nodes.push(<div key={key++} style={{ height: 5 }} />)
    } else {
      nodes.push(<div key={key++}>{renderInline(line)}</div>)
    }
  }
  return <div style={{ fontSize: 11, lineHeight: 1.6, fontFamily: 'var(--mono)' }}>{nodes}</div>
}

function renderInline(text) {
  // Split on **bold** and `code` patterns
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/)
  return parts.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={i} style={{ fontWeight: 700, color: 'var(--navy)' }}>{p.slice(2, -2)}</strong>
    if (/^`[^`]+`$/.test(p)) return <code key={i} style={{ background: '#E8ECFA', borderRadius: 3, padding: '0 3px', fontSize: 10, fontFamily: 'var(--mono)' }}>{p.slice(1, -1)}</code>
    return p
  })
}

export default function RightPanel({ account, signals = [], engineers = [], teams = [], onOutreach }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: WELCOME }])
  const [input, setInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    setMessages([{ role: 'assistant', content: WELCOME }])
    setInput('')
  }, [account?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    if (!input.trim() || chatLoading || !account) return
    const userMsg = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setChatLoading(true)
    try {
      const history = messages.slice(1).slice(-10)
      const res = await api.chat(account.id, userMsg.content, history)
      setMessages(prev => [...prev, { role: 'assistant', content: res.response }])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setChatLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (!account) {
    return (
      <div className="gp-right" style={{ justifyContent: 'center', alignItems: 'center', color: 'var(--text-faint)', fontSize: 11 }}>
        No account selected
      </div>
    )
  }

  const score = account?.signal_score ?? 0
  const sFg = score >= 85 ? '#C8005A' : score >= 60 ? '#D97706' : '#2563EB'
  const sBg = score >= 85 ? '#FFF0F5' : score >= 60 ? '#FFFBEB' : '#EFF6FF'
  const sBd = score >= 85 ? '#FBCFE8' : score >= 60 ? '#FDE68A' : '#BFDBFE'
  const sLb = score >= 85 ? 'HOT' : score >= 60 ? 'WARM' : 'COOL'

  return (
    <div className="gp-right">

      {/* Score compact pill */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span style={{ fontSize: 10, color: 'var(--text-faint)', fontFamily: 'var(--mono)', letterSpacing: '0.1em' }}>
          SIGNAL SCORE
        </span>
        <span style={{ padding: '2px 9px', borderRadius: 5, fontSize: 11, fontFamily: 'var(--mono)', fontWeight: 700, background: sBg, color: sFg, border: `1px solid ${sBd}` }}>
          {score} {sLb}
        </span>
      </div>

      {/* Engineers mini-list */}
      {engineers.length > 0 && (
        <div style={{ flexShrink: 0 }}>
          <div className="right-label">ENGINEERS ({engineers.length})</div>
          {engineers.slice(0, 4).map((eng, i) => {
            const engSigs = signals.filter(s => s.actor_login === eng.github_username)
            const heat = engSigs.reduce((best, s) => {
              const h = sigHeat(s)
              return h === 'hot' ? 'hot' : best === 'hot' ? 'hot' : h === 'warm' ? 'warm' : best
            }, 'cool')
            const team = teams.find(t => t.id === eng.team_id)
            return (
              <div key={eng.id} style={{
                display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5,
                padding: '4px 7px', borderRadius: 6,
                background: heatBg(heat), border: `1px solid ${heatBd(heat)}`
              }}>
                <div style={{
                  width: 20, height: 20, borderRadius: 4, flexShrink: 0,
                  background: PALETTE[i % 8],
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 7, fontWeight: 700, color: '#fff', fontFamily: 'var(--mono)'
                }}>{eng.github_username.slice(0, 2).toUpperCase()}</div>
                <span style={{
                  fontSize: 10, color: heatFg(heat), fontFamily: 'var(--mono)',
                  flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                }}>{eng.github_username}</span>
                {team && (
                  <span style={{
                    fontSize: 8, padding: '1px 5px', borderRadius: 3,
                    background: team.color + '22', color: team.color,
                    border: `1px solid ${team.color}44`, fontFamily: 'var(--mono)',
                    whiteSpace: 'nowrap', maxWidth: 70, overflow: 'hidden', textOverflow: 'ellipsis'
                  }}>{team.name}</span>
                )}
              </div>
            )
          })}
          {engineers.length > 4 && (
            <div style={{ fontSize: 9, color: 'var(--text-faint)', fontFamily: 'var(--mono)', paddingLeft: 4 }}>
              +{engineers.length - 4} more
            </div>
          )}
        </div>
      )}

      {/* Chat */}
      <div className="right-label" style={{ marginBottom: 0, flexShrink: 0 }}>SIGNAL CHAT</div>
      <div className="chat-thread">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.role === 'assistant' ? <MsgContent text={m.content} /> : m.content}
          </div>
        ))}
        {chatLoading && (
          <div className="chat-msg assistant" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Spinner size={10} /> Thinking...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about signals..."
          disabled={chatLoading}
          rows={2}
          style={{ resize: 'none' }}
        />
        <button className="chat-send-btn" onClick={send} disabled={!input.trim() || chatLoading}>
          &#x2191;
        </button>
      </div>

      <button className="right-cta-btn" onClick={onOutreach} style={{ flexShrink: 0 }}>
        Draft Outreach
      </button>
    </div>
  )
}
