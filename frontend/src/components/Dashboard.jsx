import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api.js'
import { Spinner, ErrorBox } from './shared/UI.jsx'
import Overview from './tabs/Overview.jsx'
import SLOTracker from './tabs/SLOTracker.jsx'
import ErrorBudget from './tabs/ErrorBudget.jsx'
import SLAConformance from './tabs/SLAConformance.jsx'
import IncidentLog from './tabs/IncidentLog.jsx'

const TABS = [
  { id: 'overview',     label: 'Overview',        icon: '◎', desc: 'System health at a glance' },
  { id: 'slo',          label: 'SLO Tracker',     icon: '⬟', desc: 'Per-SLI compliance & burn rates' },
  { id: 'budget',       label: 'Error Budget',    icon: '◑', desc: 'Budget burndown & projections' },
  { id: 'sla',          label: 'SLA Conformance', icon: '◈', desc: 'Contractual obligations & credits' },
  { id: 'incidents',    label: 'Incidents',       icon: '◆', desc: 'MTTR, MTBF & incident history' },
]

const WINDOWS = [7, 14, 30, 60, 90]

export default function Dashboard() {
  const [tab, setTab] = useState('overview')
  const [window, setWindow] = useState(30)
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const load = useCallback(async () => {
    try {
      const d = await api.dashboard(window)
      setDashboard(d)
      setLastRefresh(new Date())
      setError(null)
    } catch (e) {
      setError(`Failed to load dashboard: ${e.message}. Is the backend running? Run: uvicorn src.main:app --reload`)
    } finally {
      setLoading(false)
    }
  }, [window])

  useEffect(() => { load() }, [load])

  // Auto-refresh every 60s
  useEffect(() => {
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [load])

  const handleAnalyse = useCallback(async (service, sliType) => {
    return api.analyse(service, sliType)
  }, [])

  const overallStatus = dashboard
    ? (dashboard.services_breached > 0 ? 'breached' : dashboard.services_at_risk > 0 ? 'at_risk' : 'healthy')
    : null

  const statusDot = { healthy: '#2DD4A0', at_risk: '#F59E0B', breached: '#F87171' }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Top navbar */}
      <header style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 52 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 6,
              background: 'linear-gradient(135deg, #1E3A6E 0%, #0F2040 100%)',
              border: '1px solid rgba(74,158,255,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>⬡</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15, letterSpacing: '-0.01em' }}>Sentinel</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: -2 }}>Reliability Conformance</div>
            </div>
            {overallStatus && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginLeft: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusDot[overallStatus] }} />
                <span style={{ fontSize: 11, color: statusDot[overallStatus] }}>
                  {overallStatus === 'healthy' ? 'All services healthy' : overallStatus === 'at_risk' ? 'Services at risk' : 'SLO breach detected'}
                </span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Window selector */}
            <div style={{ display: 'flex', gap: 3, background: 'var(--bg-card)', borderRadius: 8, padding: 3, border: '1px solid var(--border)' }}>
              {WINDOWS.map(w => (
                <button key={w}
                  style={{
                    padding: '3px 8px', border: 'none', borderRadius: 6, fontSize: 11,
                    background: window === w ? 'var(--bg-surface)' : 'transparent',
                    color: window === w ? 'var(--blue)' : 'var(--text-muted)',
                    cursor: 'pointer', fontFamily: 'var(--font-ui)', fontWeight: window === w ? 600 : 400,
                    boxShadow: window === w ? '0 1px 3px rgba(0,0,0,0.3)' : 'none',
                  }}
                  onClick={() => setWindow(w)}>
                  {w}d
                </button>
              ))}
            </div>

            <button className="btn" onClick={load} style={{ padding: '4px 10px', fontSize: 11 }}>
              ↻ Refresh
            </button>

            {lastRefresh && (
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {lastRefresh.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)', position: 'sticky', top: 52, zIndex: 99 }}>
        <div className="container">
          <div style={{ display: 'flex', gap: 2, padding: '8px 0' }}>
            {TABS.map(t => (
              <button key={t.id}
                className={`tab-btn ${tab === t.id ? 'active' : ''}`}
                onClick={() => setTab(t.id)}
                title={t.desc}>
                <span style={{ fontSize: 13 }}>{t.icon}</span>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="container" style={{ padding: '24px 24px 48px' }}>
        {loading && <Spinner />}
        {error && !loading && <ErrorBox message={error} />}
        {!loading && !error && (
          <>
            {tab === 'overview'   && <Overview     dashboard={dashboard} onAnalyse={handleAnalyse} />}
            {tab === 'slo'        && <SLOTracker   dashboard={dashboard} onAnalyse={handleAnalyse} />}
            {tab === 'budget'     && <ErrorBudget  dashboard={dashboard} onAnalyse={handleAnalyse} />}
            {tab === 'sla'        && <SLAConformance dashboard={dashboard} />}
            {tab === 'incidents'  && <IncidentLog  dashboard={dashboard} onAnalyse={handleAnalyse} />}
          </>
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '12px 24px', background: 'var(--bg-surface)' }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: 'var(--text-muted)' }}>
          <span>Sentinel — Reliability Conformance · Sample data: May 2024–May 2025</span>
          <span>Backend: <a href="http://localhost:8000/docs" target="_blank" style={{ color: 'var(--blue)', textDecoration: 'none' }}>API Docs</a></span>
        </div>
      </footer>
    </div>
  )
}
