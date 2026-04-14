import { useState } from 'react'
import { Dialog, FormGroup, InputGroup, Button, HTMLSelect } from '@blueprintjs/core'

export default function AddAccountDialog({ isOpen, onClose, onSubmit }) {
  const [form, setForm] = useState({ district_domain: '', name: '', account_type: 'prospect', nces_id: '', district_legal_name: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function set(key) {
    return (e) => setForm(prev => ({ ...prev, [key]: e.target ? e.target.value : e }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.district_domain.trim()) { setError('District domain is required'); return }
    setLoading(true)
    setError('')
    try {
      await onSubmit({ ...form, name: form.name || form.district_domain })
      setForm({ district_domain: '', name: '', account_type: 'prospect', nces_id: '', district_legal_name: '' })
    } catch (err) {
      setError(err.message || 'Failed to create account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Add District Account"
      style={{ width: 420, borderRadius: 14 }}
    >
      <form onSubmit={handleSubmit} style={{ padding: 20 }}>
        <FormGroup label="District Domain" labelFor="org"
          helperText={<span style={{ fontSize: 10, color: '#6B7280' }}>e.g. lausd.net — the district’s primary web domain</span>}>
          <InputGroup id="org" placeholder="e.g. lausd.net" value={form.district_domain} onChange={set('district_domain')} />
        </FormGroup>
        <FormGroup label="Display Name" labelFor="name">
          <InputGroup id="name" placeholder="Optional — defaults to domain" value={form.name} onChange={set('name')} />
        </FormGroup>
        <FormGroup label="Type">
          <HTMLSelect value={form.account_type} onChange={set('account_type')} fill>
            <option value="prospect">Prospect</option>
            <option value="client">Partner District</option>
          </HTMLSelect>
        </FormGroup>
        <div style={{ display: 'flex', gap: 10 }}>
          <FormGroup label="NCES ID" labelFor="nces" style={{ flex: 1 }}
            helperText={<span style={{ fontSize: 10, color: '#6B7280' }}>National Center for Education Statistics district ID</span>}>
            <InputGroup id="nces" placeholder="e.g. 0622710" maxLength={20}
              value={form.nces_id}
              onChange={e => setForm(prev => ({ ...prev, nces_id: e.target.value }))}
            />
          </FormGroup>
          <FormGroup label="District Legal Name" labelFor="legalname" style={{ flex: 2 }}
            helperText={<span style={{ fontSize: 10, color: '#6B7280' }}>Full legal name used for news search (e.g. &quot;Los Angeles Unified School District&quot;)</span>}>
            <InputGroup id="legalname" placeholder="Optional" value={form.district_legal_name} onChange={set('district_legal_name')} />
          </FormGroup>
        </div>
        {error && <div style={{ color: '#C8005A', marginBottom: 12, fontSize: 12 }}>{error}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button minimal onClick={onClose}>Cancel</Button>
          <Button type="submit" intent="primary" loading={loading}>Add Account</Button>
        </div>
      </form>
    </Dialog>
  )
}
