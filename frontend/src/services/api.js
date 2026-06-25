const BASE = '/api/v1'

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`API ${path} → ${r.status}`)
  return r.json()
}

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`API POST ${path} → ${r.status}`)
  return r.json()
}

export const api = {
  dashboard:      (window = 30) => get(`/dashboard?window=${window}`),
  service:        (name, window = 30) => get(`/services/${name}?window=${window}`),
  availability:   (name, days = 30) => get(`/services/${name}/availability?days=${days}`),
  budget:         (name, days = 30) => get(`/services/${name}/budget?days=${days}`),
  heatmap:        (name, days = 90) => get(`/services/${name}/heatmap?days=${days}`),
  sla:            () => get('/sla'),
  incidents:      (service, limit = 50) => get(`/incidents?${service ? `service=${service}&` : ''}limit=${limit}`),
  analyse:        (service_name, sli_type) => post('/analyse', { service_name, sli_type }),
}
