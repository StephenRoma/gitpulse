import { useState, useEffect } from 'react'
import { Dialog, FormGroup, InputGroup, Button, HTMLSelect } from '@blueprintjs/core'

export default function EditAccountDialog({ isOpen, onClose, account, onSubmit }) {
  const [form, setForm]       = useState({ name: '', github_org: '', account_type: 'prospect' })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    if (account) {
      setForm({
        name:         account.name        || '',
        github_org:   account.github_org  || '',
        account_type: account.account_type || 'prospect',
      })
      setError('')
    }
  }, [account, isOpen])

  function set(key) {
    return (e) => setForm(prev => ({ ...prev, [key]: e.target ? e.target.value : e }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Display name is required'); return }
    setLoading(true)
    setError('')
    try {
      await onSubmit(form)
    } catch (err) {
      setError(err.message || 'Failed to update account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Account"
      style={{ width: 420, borderRadius: 14 }}
    >
      <form onSubmit={handleSubmit} style={{ padding: 20 }}>
        <FormGroup label="Display Name" labelFor="edit-name">
          <InputGroup id="edit-name" value={form.name} onChange={set('name')} />
        </FormGroup>
        <FormGroup label="GitHub Organization" labelFor="edit-org">
          <InputGroup id="edit-org" placeholder="e.g. facebook" value={form.github_org} onChange={set('github_org')} />
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
          <Button type="submit" intent="primary" loading={loading}>Save Changes</Button>
        </div>
      </form>
    </Dialog>
  )
}
