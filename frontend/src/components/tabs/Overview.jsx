import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../../services/api.js'
import { MetricCard, StatusBadge, SectionTitle, Spinner, ErrorBox, CaveatBlock, AnalyseButton, formatPct, formatMs, formatMin, formatDays, statusClass } from '../shared/UI.jsx'
import AnalysisModal from '../shared/AnalysisModal.jsx'

const svcColor = { api_gateway: '#4A9EFF', auth_service: '#F59E0B', data_pipeline: '#2DD4A0', billing_api: '#F87171' }

function HeatmapCell({ value, date }) {
  const color = value >= 99.9 ? '#2DD4A0' : value >= 99 ? '#4A9EFF' : value >= 95 ? '#F59E0B' : '#F87171'
  const opacity = value >= 99.9 ? 0.85 : value >= 99 ? 0.7 : value >= 95 ? 0.8 : 1
  return (
    <div
      title={`${date}: ${value?.toFixed(3)}%`}
      style={{ background: color, opacity, borderRadius: 2, aspectRatio: 1 }}
    />
  )
}

export default function Overview({ dashboard, onAnalyse }) {
  const [trendData, setTrendData] = useState([])
  const [heatmaps, setHeatmaps] = useState({})
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(null)

  useEffect(() => {
    if (!dashboard) return
    // fetch availability trend for all services (30d, hourly → downsample)
    Promise.all(
      dashboard.services.map(s => api.availability(s.name, 30))
    ).then(results => {
      const byTs = {}
      dashboard.services.forEach((svc, i) => {
        results[i].slice(-24 * 7).forEach(p => {  // last 7 days
          byTs[p.ts] = byTs[p.ts] ?? { ts: p.ts }
          byTs[p.ts][svc.name] = p.value
        })
      })
      const sorted = Object.values(byTs).sort((a, b) => a.ts - b.ts)
      // downsample to ~60 points
      const step = Math.max(1, Math.floor(sorted.length / 60))
      setTrendData(sorted.filter((_, i) => i % step === 0).map(p => ({
        ...p,
        time: new Date(p.ts * 1000).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }),
      })))
    }).catch(() => {})

    // heatmaps
    Promise.all(
      dashboard.services.map(s => api.heatmap(s.name, 90).then(d => [s.name, d]))
    ).then(results => {
      setHeatmaps(Object.fromEntries(results))
    }).catch(() => {})
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

  const { services, overall_availability_pct, total_incidents, services_healthy, services_at_risk, services_breached } = dashboard

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <CaveatBlock title="How to read this dashboard">
        <b>Availability</b> = % of time a service was healthy (responding within SLO bounds). 
        <b> Error Budget</b> = how much downtime remains before the SLO is breached — treat it like cash: once gone, you owe SLA credits.
        <b> Burn Rate</b> = how fast you're spending the budget (1× = exactly at limit; &gt;2× = alert-worthy).
        Data window defaults to 30 days. All values are rolling averages over the selected window.
      </CaveatBlock>

      {/* Top metrics */}
      <div className="metric-grid">
        <MetricCard
          label="Overall Availability"
          value={formatPct(overall_availability_pct)}
          sub="Across all services"
          valueClass={overall_availability_pct >= 99.9 ? 'status-healthy' : overall_availability_pct >= 99 ? 'status-at_risk' : 'status-breached'}
        />
        <MetricCard label="Services Healthy"   value={services_healthy}  sub={`${services.length} total`} valueClass="status-healthy" />
        <MetricCard label="Services At Risk"    value={services_at_risk}  sub="Error budget 5–30% left"   valueClass={services_at_risk  > 0 ? 'status-at_risk'  : ''} />
        <MetricCard label="Services Breached"   value={services_breached} sub="SLO violated"              valueClass={services_breached > 0 ? 'status-breached' : ''} />
        <MetricCard label="Total Incidents"     value={total_incidents}   sub="Rolling 30d" />
      </div>

      {/* Service cards */}
      <div>
        <SectionTitle>Service summary</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12 }}>
          {services.map(svc => {
            const budget = svc.error_budget
            const budgetPct = budget?.remaining_pct ?? 100
            const budgetColor = budgetPct > 30 ? 'var(--green)' : budgetPct > 5 ? 'var(--amber)' : 'var(--red)'
            const isAnalysing = analysing === `${svc.name}-availability`
            return (
              <div key={svc.name} className="card" style={{ borderLeft: `3px solid ${svcColor[svc.name] ?? 'var(--blue)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{svc.display_name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{svc.description}</div>
                  </div>
                  <StatusBadge status={svc.status} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
                  {[
                    { l: 'Availability', v: formatPct(svc.avg_availability_pct), ok: svc.avg_availability_pct >= (svc.slos?.[0]?.target ?? 99.9) },
                    { l: 'Error Rate',   v: formatPct(svc.avg_error_rate_pct, 3),  ok: svc.avg_error_rate_pct <= 0.1 },
                    { l: 'p99 Latency',  v: formatMs(svc.avg_latency_p99_ms),      ok: true },
                  ].map(({ l, v, ok }) => (
                    <div key={l} style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: '8px 10px' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>{l}</div>
                      <div style={{ fontFamily: 'var(--font-data)', fontSize: 14, fontWeight: 500, color: ok ? 'var(--text-primary)' : 'var(--amber)' }}>{v}</div>
                    </div>
                  ))}
                </div>

                {/* Error budget bar */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    <span>Error budget</span>
                    <span style={{ color: budgetColor, fontFamily: 'var(--font-data)' }}>{budgetPct?.toFixed(1)}% remaining</span>
                  </div>
                  <div className="progress-track" style={{ height: 6 }}>
                    <div className="progress-fill" style={{ width: `${budgetPct?.toFixed(1)}%`, background: budgetColor }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                    {formatMin(budget?.consumed_minutes)} used of {formatMin(budget?.allowed_downtime_minutes)} allowed
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {svc.tech_stack?.slice(0, 3).map(t => (
                    <span key={t} className="pill pill-gray" style={{ fontSize: 10 }}>{t}</span>
                  ))}
                  {svc.status !== 'healthy' && (
                    <AnalyseButton
                      status={svc.status}
                      loading={isAnalysing}
                      onClick={() => handleAnalyse(svc.name, 'availability')}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 7-day trend */}
      {trendData.length > 0 && (
        <div className="card">
          <SectionTitle>7-day availability trend — all services</SectionTitle>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
            Hourly availability % per service. Dips below the dotted line (99.9%) indicate SLO budget consumption.
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="rgba(99,130,190,0.1)" strokeDasharray="4 4" />
              <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} interval="preserveStartEnd" />
              <YAxis domain={[99, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickLine={false} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: 'var(--text-secondary)' }}
                itemStyle={{ color: 'var(--text-primary)' }}
                formatter={(v) => [`${v?.toFixed(3)}%`]}
              />
              {services.map(svc => (
                <Line key={svc.name} type="monotone" dataKey={svc.name} stroke={svcColor[svc.name]} strokeWidth={1.5} dot={false} name={svc.display_name} />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
            {services.map(s => (
              <span key={s.name} style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 12, height: 2, background: svcColor[s.name], display: 'inline-block', borderRadius: 2 }} />
                {s.display_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Heatmaps */}
      {Object.keys(heatmaps).length > 0 && (
        <div className="card">
          <SectionTitle>90-day availability heatmap</SectionTitle>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
            Each cell = 1 day. Green = ≥99.9% · Blue = 99–99.9% · Amber = 95–99% · Red = &lt;95%.
            Hover for exact date and value.
          </div>
          {services.map(svc => {
            const cells = heatmaps[svc.name] ?? []
            return (
              <div key={svc.name} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, color: svcColor[svc.name] }}>
                  {svc.display_name}
                </div>
                <div className="heatmap-grid">
                  {cells.map(c => <HeatmapCell key={c.date} value={c.availability_pct} date={c.date} />)}
                </div>
              </div>
            )
          })}
          <div style={{ display: 'flex', gap: 14, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
            {[['#2DD4A0','≥99.9%'],['#4A9EFF','99–99.9%'],['#F59E0B','95–99%'],['#F87171','<95%']].map(([c,l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, background: c, borderRadius: 2, display: 'inline-block' }} />
                {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {analysis && <AnalysisModal result={analysis} onClose={() => setAnalysis(null)} />}
    </div>
  )
}
