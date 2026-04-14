const INTEGRATIONS = [
  {
    name: 'HubSpot CRM',
    logo: '🟠',
    status: 'coming_soon',
    description: 'Sync accounts, contacts, and deal stages directly into HubSpot. Auto-log Quorum signals as CRM activities.',
    tags: ['CRM', 'Contacts', 'Deals'],
    color: '#FF7A59',
  },
  {
    name: 'Salesforce',
    logo: '☁️',
    status: 'coming_soon',
    description: 'Push district accounts and procurement signals into Salesforce opportunities. Map pipeline stages.',
    tags: ['CRM', 'Enterprise', 'Opportunities'],
    color: '#00A1E0',
  },
  {
    name: 'Slack',
    logo: '💬',
    status: 'coming_soon',
    description: 'Get real-time Slack alerts when a district posts a board meeting item mentioning your product category or RFP keyword.',
    tags: ['Alerts', 'Team', 'Notifications'],
    color: '#4A154B',
  },
  {
    name: 'Google Sheets',
    logo: '📊',
    status: 'coming_soon',
    description: 'Export signal feeds, RFP lists, and ESSA data to Google Sheets for custom reporting and sharing.',
    tags: ['Export', 'Reporting', 'Sheets'],
    color: '#34A853',
  },
  {
    name: 'Outreach.io',
    logo: '📧',
    status: 'coming_soon',
    description: 'Sync district contacts into Outreach sequences. Trigger sequences automatically based on buying signal scores.',
    tags: ['Sequences', 'Email', 'SDR'],
    color: '#5C4EFF',
  },
  {
    name: 'Apollo.io',
    logo: '🚀',
    status: 'coming_soon',
    description: 'Enrich district contacts using Apollo data. Find direct emails and phone numbers for superintendent and CTO personas.',
    tags: ['Enrichment', 'Contact Data', 'Prospecting'],
    color: '#FF6B35',
  },
  {
    name: 'Zapier',
    logo: '⚡',
    status: 'coming_soon',
    description: 'Connect Quorum to 5000+ apps via Zapier webhooks. Trigger any workflow when a signal is detected.',
    tags: ['Automation', 'Webhooks', 'No-code'],
    color: '#FF4A00',
  },
  {
    name: 'Monday.com',
    logo: '📅',
    status: 'coming_soon',
    description: 'Push district pipeline stages and RFP due dates into Monday.com boards for account-based marketing coordination.',
    tags: ['Project Management', 'Pipeline', 'ABM'],
    color: '#0073EA',
  },
  {
    name: 'Canopy',
    logo: '🌿',
    status: 'coming_soon',
    description: 'K-12 specific CRM. Sync your Quorum district contacts, notes, and pipelines with Canopy.',
    tags: ['K-12 CRM', 'Education', 'Contacts'],
    color: '#2D6A4F',
  },
]

function StatusBadge({ status }) {
  if (status === 'active') return (
    <span style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, padding: '2px 7px', borderRadius: 4, color: '#166534', background: '#F0FDF4', border: '1px solid #BBF7D0' }}>CONNECTED</span>
  )
  if (status === 'beta') return (
    <span style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, padding: '2px 7px', borderRadius: 4, color: '#D97706', background: '#FFFBEB', border: '1px solid #FDE68A' }}>BETA</span>
  )
  return (
    <span style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, padding: '2px 7px', borderRadius: 4, color: '#6B7280', background: '#F9FAFB', border: '1px solid #E5E7EB' }}>COMING SOON</span>
  )
}

function IntegrationCard({ integration }) {
  const isActive = integration.status === 'active'
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)', borderRadius: 11,
      padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 10,
      opacity: isActive ? 1 : 0.85,
      transition: 'box-shadow 0.15s, opacity 0.15s',
    }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 3px 14px rgba(0,0,0,0.08)'; e.currentTarget.style.opacity = '1' }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.opacity = isActive ? '1' : '0.85' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10, background: integration.color + '18',
            border: `1px solid ${integration.color}33`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
          }}>
            {integration.logo}
          </div>
          <div>
            <div style={{ fontFamily: 'var(--display)', fontWeight: 700, fontSize: 14, color: 'var(--navy)' }}>{integration.name}</div>
            <div style={{ display: 'flex', gap: 5, marginTop: 3 }}>
              {integration.tags.map(t => (
                <span key={t} style={{ fontSize: 8, fontFamily: 'var(--mono)', padding: '1px 5px', borderRadius: 3, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-faint)' }}>{t}</span>
              ))}
            </div>
          </div>
        </div>
        <StatusBadge status={integration.status} />
      </div>

      <p style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
        {integration.description}
      </p>

      <button
        disabled={integration.status !== 'active'}
        onClick={() => integration.status === 'active' ? alert('Integration settings coming soon') : null}
        style={{
          padding: '7px 14px', borderRadius: 7, cursor: isActive ? 'pointer' : 'default',
          border: `1px solid ${isActive ? integration.color : 'var(--border)'}`,
          background: isActive ? integration.color : 'transparent',
          color: isActive ? '#fff' : 'var(--text-faint)',
          fontFamily: 'var(--mono)', fontSize: 10, fontWeight: isActive ? 700 : 400,
          alignSelf: 'flex-start',
        }}>
        {isActive ? 'Configure' : 'Notify Me'}
      </button>
    </div>
  )
}

export default function IntegrationsPage() {
  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', background: 'var(--bg)' }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-faint)', letterSpacing: '0.12em', marginBottom: 6 }}>WORKFLOW TOOLS</div>
        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: 22, color: 'var(--navy)', margin: 0 }}>Explore Integrations</h1>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: 6 }}>
          Connect Quorum to your existing sales stack. Sync contacts, auto-log signals, and trigger workflows.
        </p>
      </div>

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 32, padding: '14px 20px', borderRadius: 10, background: 'var(--surface)', border: '1px solid var(--border)', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>
          <strong style={{ color: 'var(--navy)' }}>{INTEGRATIONS.length} integrations</strong> planned · <strong style={{ color: 'var(--navy)' }}>0</strong> active
        </div>
        <div style={{ flex: 1 }} />
        <a href="mailto:hello@quorum.ai" style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--magenta)', fontWeight: 700, textDecoration: 'none' }}>
          Request an integration →
        </a>
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {INTEGRATIONS.map(integration => (
          <IntegrationCard key={integration.name} integration={integration} />
        ))}
      </div>
    </div>
  )
}
