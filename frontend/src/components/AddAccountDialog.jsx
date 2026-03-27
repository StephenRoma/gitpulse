import { Dialog, Button, Intent, FormGroup, InputGroup, HTMLSelect, TextArea, Spinner } from '@blueprintjs/core'
import { useState } from 'react'
import { api } from '../api'

export default function AddAccountDialog({ isOpen, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    github_org: '',
    account_type: 'prospect',
    engineers: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function update(key, val) {
    setForm(f => ({ ...f, [key]: val }))
    setError('')
  }

  async function handleSubmit() {
    if (!form.name.trim()) { setError('Account name is required'); return }
    setLoading(true)
    setError('')
    try {
      const engineers = form.engineers
        .split(/[\n,]+/)
        .map(s => s.trim())
        .filter(Boolean)

      const result = await api.createAccount({
        name: form.name.trim(),
        github_org: form.github_org.trim(),
        account_type: form.account_type,
        engineers
      })

      setForm({ name: '', github_org: '', account_type: 'prospect', engineers: '' })
      onCreated(result.id)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Add Account"
      className="bp5-dark"
      style={{ width: 480 }}
    >
      <div style={{ padding: '20px 24px 0' }}>
        <FormGroup label="Company Name" labelInfo="(required)">
          <InputGroup
            placeholder="Acme Corp"
            value={form.name}
            onChange={e => update('name', e.target.value)}
            large
          />
        </FormGroup>

        <FormGroup label="GitHub Org / Username" helperText="The company's GitHub organization handle">
          <InputGroup
            placeholder="acme-corp"
            leftElement={<span style={{ padding: '0 8px', color: 'var(--text-muted)', lineHeight: '30px' }}>@</span>}
            value={form.github_org}
            onChange={e => update('github_org', e.target.value)}
          />
        </FormGroup>

        <FormGroup label="Account Type">
          <HTMLSelect
            value={form.account_type}
            onChange={e => update('account_type', e.target.value)}
            options={[
              { value: 'prospect', label: 'Prospect' },
              { value: 'client', label: 'Client' }
            ]}
            fill
          />
        </FormGroup>

        <FormGroup
          label="Engineer GitHub Usernames"
          helperText="One per line, or comma-separated. These are the individuals whose activity will be tracked."
        >
          <TextArea
            placeholder={"john-doe\njane-smith\nbob-builder"}
            value={form.engineers}
            onChange={e => update('engineers', e.target.value)}
            fill
            rows={4}
            style={{ fontFamily: 'var(--mono)', fontSize: 12 }}
          />
        </FormGroup>

        {error && (
          <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 12, fontFamily: 'var(--mono)' }}>
            ⚠ {error}
          </div>
        )}
      </div>

      <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8,
        borderTop: '1px solid var(--border)', marginTop: 12 }}>
        <Button text="Cancel" minimal onClick={onClose} />
        <Button
          text="Create Account"
          intent={Intent.PRIMARY}
          loading={loading}
          onClick={handleSubmit}
        />
      </div>
    </Dialog>
  )
}
