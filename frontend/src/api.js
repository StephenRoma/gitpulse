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
  updateAccount: (id, data) => req(`/accounts/${id}`, { method: 'PATCH', body: data }),
  deleteAccount: (id) => req(`/accounts/${id}`, { method: 'DELETE' }),
  getAccount: (id) => req(`/accounts/${id}`),

  getEngineers: (id) => req(`/accounts/${id}/engineers`),
  addEngineer: (id, username) => req(`/accounts/${id}/engineers`, { method: 'POST', body: { username } }),
  removeEngineer: (engineerId) => req(`/engineers/${engineerId}`, { method: 'DELETE' }),
  assignEngineerTeam: (engineerId, teamId) => req(`/engineers/${engineerId}`, { method: 'PATCH', body: { team_id: teamId } }),

  getTeams: (id) => req(`/accounts/${id}/teams`),
  createTeam: (id, data) => req(`/accounts/${id}/teams`, { method: 'POST', body: data }),
  updateTeam: (teamId, data) => req(`/teams/${teamId}`, { method: 'PATCH', body: data }),
  deleteTeam: (teamId) => req(`/teams/${teamId}`, { method: 'DELETE' }),

  getSignals: (id, limit = 300) => req(`/accounts/${id}/signals?limit=${limit}`),
  getSignalTags: (id) => req(`/accounts/${id}/signal-tags`),
  tagSignal: (signalId, theme) => req(`/signals/${signalId}/tags`, { method: 'POST', body: { theme } }),
  untagSignal: (signalId, theme) => req(`/signals/${signalId}/tags/${theme}`, { method: 'DELETE' }),

  getReport: (id) => req(`/accounts/${id}/report`),
  generateReport: (id) => req(`/accounts/${id}/report/generate`, { method: 'POST' }),
  getReportStatus: (id) => req(`/accounts/${id}/report/status`),
  getHotSignals: (limit = 10) => req(`/signals/hot?limit=${limit}`),

  getBriefing: (id) => req(`/accounts/${id}/briefing`),
  generateBriefing: (id) => req(`/accounts/${id}/briefing/generate`, { method: 'POST' }),

  importOrgMembers: (id) => req(`/accounts/${id}/import-org-members`, { method: 'POST' }),

  chat: (id, message, history = []) => req(`/accounts/${id}/chat`, { method: 'POST', body: { message, history } }),

  syncAccount: (id) => req(`/accounts/${id}/sync`, { method: 'POST' }),
  getSyncStatus: (id) => req(`/accounts/${id}/sync-status`),
  syncAll: () => req('/sync-all', { method: 'POST' }),

  health: () => req('/health'),
}
