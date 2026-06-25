import React, { useState, useEffect } from 'react'
import { api } from '../../services/api.js'
import { SectionTitle, SeverityBadge, CaveatBlock, AnalyseButton, Spinner, formatMin, formatDays } from '../shared/UI.jsx'
import AnalysisModal from '../shared/AnalysisModal.jsx'

const svcColor = { api_gateway: '#4A9EFF', auth_service: '#F59E0B', data_pipeline: '#2DD4A0', billing_api: '#F87171' }
const impactLabel = { availability_drop: 'Availability', latency_spike: 'Latency', error_rate: 'Error Rate' }

function MTTRCard({ title, value, sub, color }) {
  return (
    <div style={{ background: 'var(--bg-surface)', borderRadius: 10, padding: '14px 18px', border: '1px solid var(--border)', flex: 1 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</div>
      <div style={{ fontSize: 22, fontWeight: 500, fontFamily: 'var(--font-data)', color: color ?? 'var(--text-primary)' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

export default function IncidentLog({ dashboard, onAnalyse }) {
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [filterSvc, setFilterSvc] = useState('all')
  const [filterSev, setFilterSev] = useState('all')
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(null)

  useEffect(() => {
    api.incidents(null, 100).then(d => { setIncidents(d); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const handleAnalyse = async (service, sliType) => {
    setAnalysing(`${service}-${sliType}`)
    try {
      const result = await onAnalyse(service, sliType)
      setAnalysis(result)
    } finally { setAnalysing(null) }
  }

  if (loading) return <Spinner />

  const services = [...new Set(incidents.map(i => i.service))]
  const filtered = incidents.filter(inc =>
    (filterSvc === 'all' || inc.service === filterSvc) &&
    (filterSev === 'all' || inc.severity === filterSev)
  )

  // Per-service MTTR/MTBF from dashboard
  const svcStats = dashboard?.services?.reduce((acc, s) => {
    acc[s.name] = { mttr: s.mttr_minutes, mtbf: s.mtbf_days, status: s.status }
    return acc
  }, {}) ?? {}

  // Overall stats
  const totalDuration = incidents.reduce((a, i) => a + i.duration_minutes, 0)
  const avgMTTR = incidents.length ? (totalDuration / incidents.length).toFixed(1) : 0
  const criticalCount = incidents.filter(i => i.severity === 'critical').length

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <CaveatBlock title="MTTR and MTBF explained">
        <b>MTTR</b> (Mean Time to Recover) = average time from incident start to full service restoration — lower is better, reflects your incident response maturity.
        <b> MTBF</b> (Mean Time Between Failures) = average gap between incidents — higher is better, reflects system reliability.
        <b> Root cause</b> shown here is from post-incident review; the AI analysis button calls Claude to suggest preventive actions and missing observability.
      </CaveatBlock>

      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <MTTRCard title="Total Incidents" value={incidents.length} sub="Past 12 months" />
        <MTTRCard title="Avg MTTR" value={`${avgMTTR}m`} sub="All services" color={parseFloat(avgMTTR) < 30 ? 'var(--green)' : 'var(--amber)'} />
        <MTTRCard title="Critical incidents" value={criticalCount} sub="P0/P1 severity" color={criticalCount > 3 ? 'var(--red)' : 'var(--text-primary)'} />
        <MTTRCard title="Total downtime" value={formatMin(totalDuration)} sub="Cumulative" />
      </div>

      {/* Per-service MTTR/MTBF */}
      <div className="card">
        <SectionTitle>Reliability scorecard by service</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 12 }}>
          {dashboard?.services?.map(svc => {
            const score = Math.min(100, Math.round(
              (svc.mtbf_days / 30 * 50) + (Math.max(0, 60 - svc.mttr_minutes) / 60 * 50)
            ))
            const scoreColor = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--amber)' : 'var(--red)'
            const incCount = incidents.filter(i => i.service === svc.name).length
            return (
              <div key={svc.name} style={{
                padding: '14px 16px', background: 'var(--bg-surface)',
                borderRadius: 10, border: '1px solid var(--border)',
                borderLeft: `3px solid ${svcColor[svc.name]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ fontWeight: 600 }}>{svc.display_name}</div>
                  <span style={{ fontFamily: 'var(--font-data)', fontWeight: 500, color: scoreColor }}>{score}/100</span>
                </div>
                <div style={{ height: 4, background: 'var(--border-strong)', borderRadius: 2, marginBottom: 10, overflow: 'hidden' }}>
                  <div style={{ width: `${score}%`, height: '100%', background: scoreColor, borderRadius: 2 }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, fontSize: 11 }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>MTTR</div>
                    <div style={{ fontFamily: 'var(--font-data)', fontWeight: 500 }}>{formatMin(svc.mttr_minutes)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>MTBF</div>
                    <div style={{ fontFamily: 'var(--font-data)', fontWeight: 500 }}>{formatDays(svc.mtbf_days)}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Incidents</div>
                    <div style={{ fontFamily: 'var(--font-data)', fontWeight: 500 }}>{incCount}</div>
                  </div>
                </div>
                {svc.status !== 'healthy' && (
                  <div style={{ marginTop: 8 }}>
                    <AnalyseButton status={svc.status} loading={analysing === `${svc.name}-availability`}
                      onClick={() => handleAnalyse(svc.name, 'availability')} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Incident log */}
      <div className="card">
        <SectionTitle>Incident log</SectionTitle>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 4 }}>
            {['all', ...services].map(s => (
              <button key={s} className={`btn ${filterSvc === s ? 'btn-primary' : ''}`}
                style={{ padding: '3px 10px', fontSize: 11 }}
                onClick={() => setFilterSvc(s)}>
                {s === 'all' ? 'All services' : s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {['all', 'critical', 'high', 'medium', 'low'].map(s => (
              <button key={s} className={`btn ${filterSev === s ? 'btn-primary' : ''}`}
                style={{ padding: '3px 10px', fontSize: 11 }}
                onClick={() => setFilterSev(s)}>
                {s === 'all' ? 'All severity' : s}
              </button>
            ))}
          </div>
        </div>

        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Service</th>
                <th>Severity</th>
                <th>Impact</th>
                <th>Duration</th>
                <th>Started</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(inc => (
                <React.Fragment key={inc.id}>
                  <tr style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === inc.id ? null : inc.id)}>
                    <td style={{ fontFamily: 'var(--font-data)', fontSize: 11, color: 'var(--text-muted)' }}>{inc.id}</td>
                    <td style={{ fontWeight: 500, maxWidth: 240 }}>
                      <span style={{ marginRight: 4 }}>{expanded === inc.id ? '▼' : '▶'}</span>
                      {inc.title}
                    </td>
                    <td>
                      <span style={{ color: svcColor[inc.service] ?? 'var(--blue)', fontSize: 12 }}>
                        {inc.service?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td><SeverityBadge severity={inc.severity} /></td>
                    <td>
                      <span className="pill pill-gray" style={{ fontSize: 10 }}>{impactLabel[inc.impact] ?? inc.impact}</span>
                      {inc.availability_impact_pct > 0 && (
                        <span style={{ fontSize: 10, color: 'var(--red)', marginLeft: 4 }}>-{inc.availability_impact_pct}%</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-data)', fontSize: 12 }}>{formatMin(inc.duration_minutes)}</td>
                    <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{inc.started_at?.slice(0, 16).replace('T', ' ')}</td>
                    <td>
                      <AnalyseButton
                        status={inc.severity === 'critical' || inc.severity === 'high' ? 'breached' : 'at_risk'}
                        loading={analysing === `${inc.service}-availability`}
                        onClick={e => { e.stopPropagation(); handleAnalyse(inc.service, 'availability') }}
                      />
                    </td>
                  </tr>
                  {expanded === inc.id && (
                    <tr>
                      <td colSpan={8} style={{ padding: 0 }}>
                        <div style={{
                          padding: '14px 20px', background: 'var(--bg-surface)',
                          borderLeft: `3px solid ${svcColor[inc.service] ?? 'var(--blue)'}`,
                          fontSize: 13, lineHeight: 1.7,
                        }}>
                          <div style={{ marginBottom: 6 }}>
                            <b style={{ color: 'var(--text-muted)', fontSize: 11 }}>ROOT CAUSE</b>
                          </div>
                          <div style={{ color: 'var(--text-primary)' }}>{inc.root_cause}</div>
                          <div style={{ marginTop: 10, display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-secondary)' }}>
                            <span>Started: {inc.started_at?.slice(0, 19).replace('T', ' ')} UTC</span>
                            <span>Resolved: {inc.resolved_at?.slice(0, 19).replace('T', ' ')} UTC</span>
                            <span>Duration: {formatMin(inc.duration_minutes)}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
            No incidents match the current filter.
          </div>
        )}
      </div>

      {analysis && <AnalysisModal result={analysis} onClose={() => setAnalysis(null)} />}
    </div>
  )
}
