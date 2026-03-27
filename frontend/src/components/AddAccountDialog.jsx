import { useState } from 'react'
import { Dialog, FormGroup, InputGroup, Button, HTMLSelect } from '@blueprintjs/core'

export default function AddAccountDialog({ isOpen, onClose, onSubmit }) {
  const [form, setForm] = useState({ github_org: '', name: '', account_type: 'prospect' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function set(key) {
    return (e) => setForm(prev => ({ ...prev, [key]: e.target ? e.target.value : e }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.github_org.trim()) { setError('GitHub org is required'); return }
    setLoading(true)
    setError('')
    try {
      await onSubmit({ ...form, name: form.name || form.github_org })
      setForm({ github_org: '', name: '', account_type: 'prospect' })
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
      title="Add Account"
      style={{ width: 420, borderRadius: 14 }}
    >
      <form onSubmit={handleSubmit} style={{ padding: 20 }}>
        <FormGroup label="GitHub Organization" labelFor="org">
          <InputGroup id="org" placeholder="e.g. facebook" value={form.github_org} onChange={set('github_org')} />
        </FormGroup>
        <FormGroup label="Display Name" labelFor="name">
          <InputGroup id="name" placeholder="Optional" value={form.name} onChange={set('name')} />
        </FormGroup>
        <FormGroup label="Type">
          <HTMLSelect value={form.account_type} onChange={set('account_type')} fill>
            <option value="prospect">Pipeline</option>
            <option value="client">Active Client</option>
          </HTMLSelect>
        </FormGroup>
        {error && <div style={{ color: '#C8005A', marginBottom: 12, fontSize: 12 }}>{error}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button minimal onClick={onClose}>Cancel</Button>
          <Button type="submit" intent="primary" loading={loading}>Add Account</Button>
        </div>
      </form>
    </Dialog>
  )
}
