import React, { useState } from 'react'
import { SectionTitle, StatusBadge, BurnPill, ComplianceBar, AnalyseButton, CaveatBlock, formatPct, formatMs, Spinner } from '../shared/UI.jsx'
import AnalysisModal from '../shared/AnalysisModal.jsx'

const SLI_META = {
  availability: { icon: '🟢', desc: 'The % of time the service responded successfully within the agreed time window. SLO breach = downtime affecting users.' },
  error_rate:   { icon: '🔴', desc: 'The % of requests returning 5xx errors. High error rate directly impacts user experience and often signals code or infrastructure issues.' },
  latency_p99:  { icon: '⏱',  desc: 'The 99th percentile response time in milliseconds — 1 in 100 requests takes this long or more. p99 is chosen over average because it reveals tail latency that impacts the slowest users.' },
}

function SLIRow({ sli, service, onAnalyse, analysing }) {
  const met = sli.direction === 'higher_is_better'
    ? sli.current_value >= sli.target
    : sli.current_value <= sli.target

  const displayVal = sli.unit === 'ms' ? formatMs(sli.current_value)
    : sli.unit === '%' ? formatPct(sli.current_value, 3) : sli.current_value

  const targetDisplay = sli.unit === 'ms'
    ? `≤ ${sli.target}ms`
    : sli.direction === 'higher_is_better' ? `≥ ${sli.target}%` : `≤ ${sli.target}%`

  const key = `${service}-${sli.name}`

  return (
    <tr>
      <td>
        <div style={{ fontWeight: 500 }}>{SLI_META[sli.name]?.icon} {sli.display_name}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }} title={SLI_META[sli.name]?.desc}>
          {SLI_META[sli.name]?.desc?.slice(0, 80)}…
        </div>
      </td>
      <td style={{ fontFamily: 'var(--font-data)', fontWeight: 500 }}>
        <span className={`status-${sli.status}`}>{displayVal}</span>
      </td>
      <td style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-data)', fontSize: 12 }}>{targetDisplay}</td>
      <td style={{ minWidth: 120 }}>
        <ComplianceBar current={sli.current_value} target={sli.target} direction={sli.direction} />
      </td>
      <td>
        <div style={{ display: 'flex', gap: 4 }}>
          <BurnPill rate={sli.burn_rate_1h} label="1h " />
          <BurnPill rate={sli.burn_rate_6h} label="6h " />
          <BurnPill rate={sli.burn_rate_24h} label="24h " />
        </div>
      </td>
      <td><StatusBadge status={sli.status} /></td>
      <td>
        <AnalyseButton status={sli.status} loading={analysing === key} onClick={() => onAnalyse(service, sli.name, key)} />
      </td>
    </tr>
  )
}

export default function SLOTracker({ dashboard, onAnalyse }) {
  const [filter, setFilter] = useState('all')
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(null)

  if (!dashboard) return <Spinner />

  const handleAnalyse = async (service, sliType, key) => {
    setAnalysing(key)
    try {
      const result = await onAnalyse(service, sliType)
      setAnalysis(result)
    } finally {
      setAnalysing(null)
    }
  }

  const statuses = ['all', 'breached', 'at_risk', 'healthy']

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <CaveatBlock title="How to read this table">
        Each row is a single <b>Service Level Indicator (SLI)</b> measured against its <b>SLO target</b>.
        The <b>compliance bar</b> shows how close you are to the target (full = meeting SLO).
        <b> Burn rates</b> at 1h / 6h / 24h show how fast you're consuming the error budget: 
        1× = right at the limit, &gt;2× = budget exhausting faster than it can recover over the window.
        Click <b>Analyse</b> on amber/red rows to get AI-powered root cause suggestions.
      </CaveatBlock>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Filter:</span>
        {statuses.map(s => (
          <button key={s} className={`btn ${filter === s ? 'btn-primary' : ''}`}
            style={{ padding: '4px 12px', fontSize: 12 }}
            onClick={() => setFilter(s)}>
            {s === 'all' ? 'All SLIs' : s.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </button>
        ))}
      </div>

      {dashboard.services.map(svc => {
        const slis = svc.slos?.flatMap(slo => slo.slis ?? []) ?? []
        const filtered = filter === 'all' ? slis : slis.filter(s => s.status === filter)
        if (!filtered.length) return null

        return (
          <div key={svc.name} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{svc.display_name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{svc.description}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <StatusBadge status={svc.status} />
                <span className="pill pill-gray">{svc.tier}</span>
              </div>
            </div>

            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '28%' }}>SLI</th>
                    <th>Current</th>
                    <th>Target</th>
                    <th>Compliance</th>
                    <th>Burn Rates (1h / 6h / 24h)</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(sli => (
                    <SLIRow
                      key={sli.name}
                      sli={sli}
                      service={svc.name}
                      onAnalyse={handleAnalyse}
                      analysing={analysing}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}

      {analysis && <AnalysisModal result={analysis} onClose={() => setAnalysis(null)} />}
    </div>
  )
}
