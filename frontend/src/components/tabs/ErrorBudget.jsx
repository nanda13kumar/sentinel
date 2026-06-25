import React, { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { api } from '../../services/api.js'
import { SectionTitle, BurnPill, CaveatBlock, AnalyseButton, formatMin, Spinner } from '../shared/UI.jsx'
import AnalysisModal from '../shared/AnalysisModal.jsx'

const svcColor = { api_gateway: '#4A9EFF', auth_service: '#F59E0B', data_pipeline: '#2DD4A0', billing_api: '#F87171' }

function BudgetRing({ pct, color, size = 80 }) {
  const r = size * 0.38
  const circ = 2 * Math.PI * r
  const dash = circ * (Math.max(0, pct) / 100)
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border-strong)" strokeWidth={7} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={7}
        strokeDasharray={`${dash.toFixed(1)} ${(circ - dash).toFixed(1)}`}
        strokeDashoffset={circ * 0.25} strokeLinecap="round" />
      <text x={size/2} y={size/2+1} textAnchor="middle" dominantBaseline="middle"
        fontSize={13} fontWeight={500} fill={color} fontFamily="var(--font-data)">
        {pct.toFixed(0)}%
      </text>
    </svg>
  )
}

export default function ErrorBudget({ dashboard, onAnalyse }) {
  const [budgetSeries, setBudgetSeries] = useState({})
  const [loading, setLoading] = useState(true)
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(null)

  useEffect(() => {
    if (!dashboard) return
    Promise.all(
      dashboard.services.map(s => api.budget(s.name, 30).then(d => [s.name, d]))
    ).then(results => {
      const series = Object.fromEntries(results)
      // downsample each to ~60 points
      const downsampled = {}
      for (const [name, data] of Object.entries(series)) {
        const step = Math.max(1, Math.floor(data.length / 60))
        downsampled[name] = data.filter((_, i) => i % step === 0).map(p => ({
          ...p,
          time: new Date(p.ts * 1000).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }),
        }))
      }
      setBudgetSeries(downsampled)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [dashboard])

  const handleAnalyse = async (service, sliType) => {
    setAnalysing(`${service}-${sliType}`)
    try {
      const result = await onAnalyse(service, sliType)
      setAnalysis(result)
    } finally {
      setAnalysing(null)
    }
  }

  if (!dashboard) return <Spinner />

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <CaveatBlock title="Error budget explained">
        The <b>error budget</b> is the allowable downtime before an SLO is violated. For a 99.9% SLO over 30 days,
        the budget is <b>43.2 minutes</b>. The <b>burndown chart</b> shows remaining budget over time — a steep drop
        means an incident consumed budget. A budget hitting 0% means the SLA is breached and credits may be owed.
        The <b>ideal slope</b> (dotted) is what linear consumption looks like — if the line is steeper, you're burning faster.
      </CaveatBlock>

      {/* Overview rings */}
      <div className="card">
        <SectionTitle>Error budget remaining — all services</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {dashboard.services.map(svc => {
            const pct = svc.error_budget?.remaining_pct ?? 100
            const color = pct > 30 ? 'var(--green)' : pct > 5 ? 'var(--amber)' : 'var(--red)'
            const budget = svc.error_budget
            return (
              <div key={svc.name} style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '14px 16px', background: 'var(--bg-surface)',
                borderRadius: 10, border: '1px solid var(--border)',
              }}>
                <BudgetRing pct={pct} color={color} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{svc.display_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {formatMin(budget?.remaining_minutes)} left
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    of {formatMin(budget?.allowed_downtime_minutes)} allowed
                  </div>
                  <div style={{ marginTop: 6, display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Burn:</span>
                    <BurnPill rate={budget?.burn_rate_current} />
                    {svc.status !== 'healthy' && (
                      <AnalyseButton
                        status={svc.status}
                        loading={analysing === `${svc.name}-availability`}
                        onClick={() => handleAnalyse(svc.name, 'availability')}
                      />
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Per-service burndown charts */}
      {loading ? <Spinner /> : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 16 }}>
          {dashboard.services.map(svc => {
            const data = budgetSeries[svc.name] ?? []
            const color = svcColor[svc.name] ?? 'var(--blue)'
            // add ideal slope line
            const withIdeal = data.map((p, i) => ({
              ...p,
              ideal: parseFloat((100 - (i / Math.max(data.length - 1, 1)) * 100).toFixed(2)),
            }))
            return (
              <div key={svc.name} className="card card-sm">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{svc.display_name}</div>
                  <BurnPill rate={svc.error_budget?.burn_rate_current} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                  Budget remaining over 30 days · dashed = ideal linear slope
                </div>
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={withIdeal} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id={`g-${svc.name}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                        <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(99,130,190,0.08)" strokeDasharray="4 4" />
                    <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} interval="preserveStartEnd" />
                    <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} tickFormatter={v => `${v}%`} />
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 11 }}
                      formatter={(v, n) => [typeof v === 'number' ? `${v.toFixed(2)}%` : v, n === 'budget_remaining_pct' ? 'Remaining' : 'Ideal']}
                    />
                    <ReferenceLine y={0} stroke="var(--red)" strokeDasharray="3 3" />
                    <Area type="monotone" dataKey="ideal" stroke="rgba(255,255,255,0.2)" strokeDasharray="4 4" strokeWidth={1} fill="none" dot={false} />
                    <Area type="monotone" dataKey="budget_remaining_pct" stroke={color} strokeWidth={2} fill={`url(#g-${svc.name})`} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )
          })}
        </div>
      )}

      {/* Multi-window burn rates */}
      <div className="card">
        <SectionTitle>Multi-window burn rate comparison</SectionTitle>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 14 }}>
          Burn rate at different time windows. 1h burn rate reacts quickly to incidents; 24h shows sustained trends.
          Rule of thumb: if 1h burn rate &gt; 14.4×, budget will exhaust in &lt; 1 hour at current rate.
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>1h Burn</th>
                <th>6h Burn</th>
                <th>24h Burn</th>
                <th>Budget Left</th>
                <th>Projected Exhaustion</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.services.map(svc => {
                const slis = svc.slos?.flatMap(s => s.slis ?? [])
                const avail = slis?.find(s => s.name === 'availability')
                const budget = svc.error_budget
                const proj = budget?.projected_exhaustion_days
                return (
                  <tr key={svc.name}>
                    <td style={{ fontWeight: 500 }}>{svc.display_name}</td>
                    <td><BurnPill rate={avail?.burn_rate_1h ?? 0} label="1h " /></td>
                    <td><BurnPill rate={avail?.burn_rate_6h ?? 0} label="6h " /></td>
                    <td><BurnPill rate={avail?.burn_rate_24h ?? 0} label="24h " /></td>
                    <td style={{ fontFamily: 'var(--font-data)' }}>
                      <span className={budget?.remaining_pct > 30 ? 'status-healthy' : budget?.remaining_pct > 5 ? 'status-at_risk' : 'status-breached'}>
                        {budget?.remaining_pct?.toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                      {proj ? `~${proj} days` : '—'}
                    </td>
                    <td>
                      <span className={`pill ${svc.status === 'healthy' ? 'pill-green' : svc.status === 'at_risk' ? 'pill-amber' : 'pill-red'}`}>
                        {svc.status?.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {analysis && <AnalysisModal result={analysis} onClose={() => setAnalysis(null)} />}
    </div>
  )
}
