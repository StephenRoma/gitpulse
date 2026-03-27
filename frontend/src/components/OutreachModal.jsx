import { useState } from 'react'
import { Dialog, Button } from '@blueprintjs/core'

export default function OutreachModal({ isOpen, onClose, account, briefing }) {
  const [copied, setCopied] = useState(false)

  const content = briefing?.content
  const lines = []
  if (content?.summary)            lines.push(content.summary)
  if (content?.opportunities?.length) {
    lines.push('\nOpportunities:')
    content.opportunities.forEach(o => lines.push(`- ${o}`))
  }
  if (content?.key_themes?.length) {
    lines.push('\nKey Themes:')
    content.key_themes.forEach(t => lines.push(`- ${t}`))
  }
  if (content?.recommended_action) lines.push(`\nRecommended Action:\n${content.recommended_action}`)

  const text = lines.join('\n') || 'No briefing data available. Generate a briefing first.'

  async function handleCopy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={`Outreach - ${account?.name || account?.github_org || ''}`}
      style={{ width: 520, borderRadius: 14 }}
    >
      <div style={{ padding: 20 }}>
        <textarea className="outreach-textarea" readOnly value={text} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
          <Button minimal onClick={onClose}>Close</Button>
          <Button intent="primary" onClick={handleCopy}>
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
