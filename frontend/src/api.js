const BASE = '/api'

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  getAccounts: () => req('/accounts'),
  createAccount: (data) => req('/accounts', { method: 'POST', body: data }),
  deleteAccount: (id) => req(`/accounts/${id}`, { method: 'DELETE' }),
  getAccount: (id) => req(`/accounts/${id}`),

  getEngineers: (id) => req(`/accounts/${id}/engineers`),
  addEngineer: (id, username) => req(`/accounts/${id}/engineers`, { method: 'POST', body: { username } }),
  removeEngineer: (engineerId) => req(`/engineers/${engineerId}`, { method: 'DELETE' }),

  getSignals: (id, limit = 50) => req(`/accounts/${id}/signals?limit=${limit}`),

  getBriefing: (id) => req(`/accounts/${id}/briefing`),
  generateBriefing: (id) => req(`/accounts/${id}/briefing/generate`, { method: 'POST' }),

  importOrgMembers: (id) => req(`/accounts/${id}/import-org-members`, { method: 'POST' }),

  chat: (id, message, history = []) => req(`/accounts/${id}/chat`, { method: 'POST', body: { message, history } }),

  syncAccount: (id) => req(`/accounts/${id}/sync`, { method: 'POST' }),
  getSyncStatus: (id) => req(`/accounts/${id}/sync-status`),
  syncAll: () => req('/sync-all', { method: 'POST' }),

  health: () => req('/health'),
}
