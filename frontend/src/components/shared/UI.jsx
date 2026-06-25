import React from 'react'

// ── Status helpers ──────────────────────────────────────────────────────────
export const statusLabel = (s) => ({ healthy: 'Healthy', at_risk: 'At Risk', breached: 'Breached' }[s] ?? s)
export const statusClass = (s) => ({ healthy: 'status-healthy', at_risk: 'status-at_risk', breached: 'status-breached' }[s] ?? '')
export const statusPill  = (s) => ({ healthy: 'pill-green', at_risk: 'pill-amber', breached: 'pill-red' }[s] ?? 'pill-gray')
export const severityPill = (s) => ({ critical: 'pill-red', high: 'pill-amber', medium: 'pill-blue', low: 'pill-gray' }[s] ?? 'pill-gray')

export const formatPct = (v, decimals = 3) => (typeof v === 'number' ? v.toFixed(decimals) + '%' : '—')
export const formatMs  = (v) => (typeof v === 'number' ? Math.round(v) + ' ms' : '—')
export const formatMin = (v) => {
  if (!v) return '—'
  if (v < 60) return `${Math.round(v)}m`
  return `${Math.floor(v / 60)}h ${Math.round(v % 60)}m`
}
export const formatDays = (v) => (typeof v === 'number' ? `${v.toFixed(1)}d` : '—')

export const burnClass = (r) => r < 1 ? 'pill-green' : r < 2 ? 'pill-amber' : 'pill-red'
export const burnLabel = (r) => (typeof r === 'number' ? `${r.toFixed(1)}×` : '—')

// ── StatusBadge ─────────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  return <span className={`pill ${statusPill(status)}`}>{statusLabel(status)}</span>
}

// ── SeverityBadge ───────────────────────────────────────────────────────────
export function SeverityBadge({ severity }) {
  return <span className={`pill ${severityPill(severity)}`}>{severity?.toUpperCase()}</span>
}

// ── BurnPill ────────────────────────────────────────────────────────────────
export function BurnPill({ rate, label }) {
  return (
    <span className={`pill ${burnClass(rate)}`} title={`${label ?? ''}burn rate: ${burnLabel(rate)} — ${rate < 1 ? 'consuming budget slower than allowed' : rate < 2 ? 'moderate over-consumption' : 'fast budget exhaustion'}`}>
      {burnLabel(rate)}
    </span>
  )
}

// ── ComplianceBar ───────────────────────────────────────────────────────────
export function ComplianceBar({ current, target, direction = 'higher_is_better' }) {
  const met = direction === 'higher_is_better' ? current >= target : current <= target
  const pct = direction === 'higher_is_better'
    ? Math.min(100, (current / target) * 100)
    : Math.min(100, (target / Math.max(current, 0.001)) * 100)
  const color = met ? 'var(--green)' : pct > 80 ? 'var(--amber)' : 'var(--red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
      <div className="progress-track" style={{ flex: 1 }}>
        <div className="progress-fill" style={{ width: `${pct.toFixed(1)}%`, background: color }} />
      </div>
    </div>
  )
}

// ── MetricCard ──────────────────────────────────────────────────────────────
export function MetricCard({ label, value, sub, valueClass = '' }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${valueClass}`}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  )
}

// ── SectionTitle ─────────────────────────────────────────────────────────────
export function SectionTitle({ children }) {
  return <div className="section-title">{children}</div>
}

// ── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%',
        border: '2px solid var(--border-strong)',
        borderTopColor: 'var(--blue)',
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Error box ────────────────────────────────────────────────────────────────
export function ErrorBox({ message }) {
  return (
    <div style={{
      padding: 16, background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.3)',
      borderRadius: 'var(--radius-md)', color: 'var(--red)', fontSize: 13,
    }}>
      ⚠ {message}
    </div>
  )
}

// ── AnalyseButton ─────────────────────────────────────────────────────────────
export function AnalyseButton({ status, onClick, loading }) {
  if (status === 'healthy') return null
  const cls = status === 'breached' ? 'btn-analyse-red' : 'btn-analyse-amber'
  return (
    <button className={`btn ${cls}`} onClick={onClick} disabled={loading}>
      {loading ? '⏳' : '🔍'} {loading ? 'Analysing…' : 'Analyse'}
    </button>
  )
}

// ── CaveatBlock ───────────────────────────────────────────────────────────────
export function CaveatBlock({ title = 'How to read this', children }) {
  return (
    <div className="caveat-box" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--purple)' }}>ℹ {title}</div>
      {children}
    </div>
  )
}

// ── InfoBox ───────────────────────────────────────────────────────────────────
export function InfoBox({ children }) {
  return <div className="info-box">{children}</div>
}

// ── Custom recharts tooltip ───────────────────────────────────────────────────
export function ChartTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border-strong)',
      borderRadius: 8, padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color ?? 'var(--text-primary)', fontFamily: 'var(--font-data)' }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(3) : p.value}{unit}
        </div>
      ))}
    </div>
  )
}
