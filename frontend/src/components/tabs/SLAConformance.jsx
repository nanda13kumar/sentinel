import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../../services/api.js'
import { SectionTitle, CaveatBlock, Spinner, formatPct, formatMin } from '../shared/UI.jsx'

const tierColor = { enterprise: '#F87171', business: '#F59E0B', starter: '#4A9EFF', internal: '#2DD4A0' }

export default function SLAConformance({ dashboard }) {
  const [sla, setSla] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.sla().then(d => { setSla(d); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />
  if (!sla) return null

  // Build unified monthly chart data
  const allMonths = [...new Set(sla.flatMap(t => t.monthly_trend?.map(m => m.month) ?? []))].sort()
  const trendData = allMonths.map(month => {
    const row = { month }
    sla.forEach(t => {
      const entry = t.monthly_trend?.find(m => m.month === month)
      if (entry) row[t.tier] = entry.actual_pct
    })
    return row
  })

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <CaveatBlock title="SLA vs SLO — what's the difference?">
        An <b>SLO</b> (Service Level Objective) is an internal reliability target your team owns.
        An <b>SLA</b> (Service Level Agreement) is a contractual commitment to customers — violating it means <b>service credits are owed</b>.
        SLOs should be more ambitious than SLAs; the SLO acts as a "warning zone" so you fix problems before the SLA breach triggers credits.
        This table shows current MTD compliance per customer tier and any credits owed.
      </CaveatBlock>

      {/* Compliance cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        {sla.map(tier => {
          const color = tierColor[tier.tier] ?? 'var(--blue)'
          const pctDiff = (tier.actual_pct - tier.target_pct).toFixed(4)
          const headroom = tier.actual_pct >= tier.target_pct ? `+${pctDiff}pp headroom` : `${pctDiff}pp below target`
          return (
            <div key={tier.name} className="card" style={{
              borderTop: `3px solid ${color}`,
              borderLeft: tier.compliant ? '1px solid var(--border)' : '1px solid rgba(248,113,113,0.4)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{tier.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Target: {tier.target_pct}%</div>
                </div>
                <span className={`pill ${tier.compliant ? 'pill-green' : 'pill-red'}`}>
                  {tier.compliant ? 'Compliant' : 'Breached'}
                </span>
              </div>
              <div style={{ fontFamily: 'var(--font-data)', fontSize: 24, fontWeight: 500,
                color: tier.compliant ? 'var(--text-primary)' : 'var(--red)', marginBottom: 4 }}>
                {tier.actual_pct?.toFixed(4)}%
              </div>
              <div style={{ fontSize: 11, color: tier.compliant ? 'var(--green)' : 'var(--red)', marginBottom: 10 }}>
                {headroom}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>
                Budget remaining: <b style={{ fontFamily: 'var(--font-data)' }}>{formatMin(tier.remaining_budget_minutes)}</b>
              </div>
              {!tier.compliant && tier.credits_owed_pct > 0 && (
                <div style={{
                  marginTop: 8, padding: '6px 10px',
                  background: 'var(--red-dim)', borderRadius: 6, fontSize: 11,
                  color: 'var(--red)', border: '1px solid rgba(248,113,113,0.3)',
                }}>
                  ⚠ Credits owed: {tier.credits_owed_pct}% of monthly invoice
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Conformance table */}
      <div className="card">
        <SectionTitle>SLA obligation detail — 30-day window</SectionTitle>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Customer tier</th>
                <th>SLA target</th>
                <th>Actual (MTD)</th>
                <th>Budget (min)</th>
                <th>Consumed (min)</th>
                <th>Remaining</th>
                <th>Status</th>
                <th>Credits owed</th>
              </tr>
            </thead>
            <tbody>
              {sla.map(tier => {
                const totalMin = 30 * 24 * 60
                const allowed = totalMin * (1 - tier.target_pct / 100)
                const consumed = Math.max(0, allowed - tier.remaining_budget_minutes)
                return (
                  <tr key={tier.name}>
                    <td>
                      <div style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: tierColor[tier.tier] ?? 'var(--blue)', display: 'inline-block' }} />
                        {tier.name}
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-data)', fontSize: 12 }}>{tier.target_pct}%</td>
                    <td style={{ fontFamily: 'var(--font-data)', fontWeight: 500, color: tier.compliant ? 'var(--text-primary)' : 'var(--red)' }}>
                      {tier.actual_pct?.toFixed(4)}%
                    </td>
                    <td style={{ fontFamily: 'var(--font-data)', fontSize: 12, color: 'var(--text-secondary)' }}>{allowed.toFixed(1)}</td>
                    <td style={{ fontFamily: 'var(--font-data)', fontSize: 12, color: consumed > allowed ? 'var(--red)' : 'var(--text-secondary)' }}>
                      {consumed.toFixed(1)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-data)', fontSize: 12 }}>
                      <span style={{ color: tier.remaining_budget_minutes > 5 ? 'var(--green)' : 'var(--red)' }}>
                        {tier.remaining_budget_minutes.toFixed(1)} min
                      </span>
                    </td>
                    <td>
                      <span className={`pill ${tier.compliant ? 'pill-green' : 'pill-red'}`}>
                        {tier.compliant ? '✓ OK' : '✗ Breach'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-data)', color: !tier.compliant && tier.credits_owed_pct > 0 ? 'var(--red)' : 'var(--text-secondary)', fontWeight: !tier.compliant ? 600 : 400 }}>
                      {tier.credits_owed_pct > 0 ? `${tier.credits_owed_pct}%` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Monthly trend */}
      {trendData.length > 0 && (
        <div className="card">
          <SectionTitle>12-month availability trend by SLA tier</SectionTitle>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 14 }}>
            Monthly average availability per tier. Dotted lines at tier SLA targets — any dip below = breach month.
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="rgba(99,130,190,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} />
              <YAxis domain={[99, 100.01]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 12 }}
                formatter={(v) => [typeof v === 'number' ? `${v.toFixed(4)}%` : v]}
              />
              {sla.map(t => (
                <Line key={t.tier} type="monotone" dataKey={t.tier} stroke={tierColor[t.tier]} strokeWidth={2} dot={{ r: 3, fill: tierColor[t.tier] }} name={t.name} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 14, marginTop: 10, flexWrap: 'wrap' }}>
            {sla.map(t => (
              <span key={t.tier} style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 16, height: 2, background: tierColor[t.tier], display: 'inline-block', borderRadius: 2 }} />
                {t.name} ({t.target_pct}% SLA)
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
