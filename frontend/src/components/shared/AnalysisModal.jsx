import React from 'react'
import { SeverityBadge } from './UI.jsx'

const Section = ({ title, color = 'var(--blue)', children }) => (
  <div style={{ marginBottom: 20 }}>
    <div style={{
      fontSize: 11, fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase',
      color, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8,
    }}>
      {title}
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
    {children}
  </div>
)

const ActionItem = ({ item, idx }) => (
  <div style={{
    padding: '10px 14px', background: 'var(--bg-card)', borderRadius: 8,
    border: '1px solid var(--border)', marginBottom: 8,
    borderLeft: '3px solid var(--blue)',
  }}>
    <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{item.action}</div>
    <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 12 }}>
      <span>📦 {item.component}</span>
    </div>
    {item.rationale && (
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>↳ {item.rationale}</div>
    )}
  </div>
)

const GapItem = ({ gap }) => (
  <div style={{
    padding: '12px 14px', background: 'rgba(167,139,250,0.05)',
    borderRadius: 8, border: '1px solid rgba(167,139,250,0.2)', marginBottom: 8,
  }}>
    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--purple)', marginBottom: 4 }}>
      ⚠ {gap.gap}
    </div>
    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
      <b>Impact:</b> {gap.impact}
    </div>
    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
      <b>How to close:</b> {gap.how_to_close}
    </div>
    {gap.automation_trigger && (
      <div style={{
        fontSize: 11, marginTop: 6, padding: '6px 10px',
        background: 'rgba(74,158,255,0.08)', borderRadius: 6,
        border: '1px solid rgba(74,158,255,0.2)', color: 'var(--blue)',
        fontFamily: 'var(--font-data)',
      }}>
        🤖 Auto-trigger: {gap.automation_trigger}
      </div>
    )}
  </div>
)

const RemediationItem = ({ r }) => (
  <div style={{
    padding: '12px 14px', background: 'var(--green-dim)',
    borderRadius: 8, border: '1px solid rgba(45,212,160,0.25)', marginBottom: 8,
  }}>
    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
      <b style={{ color: 'var(--green)' }}>Trigger:</b> {r.trigger_condition}
    </div>
    <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>→ {r.action}</div>
    {r.implementation_sketch && (
      <div style={{
        fontSize: 11, padding: '6px 10px', marginTop: 6,
        background: 'var(--bg-card)', borderRadius: 6, fontFamily: 'var(--font-data)',
        color: 'var(--text-secondary)', border: '1px solid var(--border)',
      }}>
        {r.implementation_sketch}
      </div>
    )}
  </div>
)

export default function AnalysisModal({ result, onClose }) {
  if (!result) return null

  const confidenceColor = { high: 'var(--green)', medium: 'var(--amber)', low: 'var(--red)' }[result.confidence] ?? 'var(--text-secondary)'

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box fade-in">
        {/* Header */}
        <div className="modal-header">
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 2 }}>
              🔍 AI Reliability Analysis
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {result.service_name} · {result.sli_type} · {result.ai_model}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, color: confidenceColor, border: `1px solid ${confidenceColor}`, padding: '2px 8px', borderRadius: 20 }}>
              {result.confidence?.toUpperCase()} CONFIDENCE
            </span>
            <button className="btn" onClick={onClose} style={{ padding: '4px 10px' }}>✕</button>
          </div>
        </div>

        <div className="modal-body">
          {/* Summary */}
          <div style={{
            padding: '14px 16px', marginBottom: 20,
            background: 'var(--bg-card)', borderRadius: 8, border: '1px solid var(--border)',
            fontSize: 13, lineHeight: 1.6, color: 'var(--text-primary)',
          }}>
            {result.summary}
          </div>

          {/* Root causes */}
          {result.root_cause_hypotheses?.length > 0 && (
            <Section title="Root cause hypotheses" color="var(--red)">
              {result.root_cause_hypotheses.map((h, i) => (
                <div key={i} style={{
                  padding: '10px 14px', marginBottom: 8, borderRadius: 8,
                  background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.2)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--red)', fontFamily: 'var(--font-data)' }}>#{h.rank}</span>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{h.hypothesis}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 11, color: { high: 'var(--red)', medium: 'var(--amber)', low: 'var(--text-secondary)' }[h.confidence] ?? 'var(--text-secondary)' }}>
                      {h.confidence}
                    </span>
                  </div>
                  {h.evidence && <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Evidence: {h.evidence}</div>}
                </div>
              ))}
            </Section>
          )}

          {/* Action items */}
          {result.action_items && Object.keys(result.action_items).length > 0 && (
            <Section title="Action items" color="var(--blue)">
              {result.action_items.immediate?.length > 0 && (
                <>
                  <div style={{ fontSize: 11, color: 'var(--red)', fontWeight: 600, marginBottom: 6 }}>🚨 IMMEDIATE</div>
                  {result.action_items.immediate.map((a, i) => <ActionItem key={i} item={a} />)}
                </>
              )}
              {result.action_items.short_term?.length > 0 && (
                <>
                  <div style={{ fontSize: 11, color: 'var(--amber)', fontWeight: 600, margin: '12px 0 6px' }}>⚡ SHORT TERM (1–2 weeks)</div>
                  {result.action_items.short_term.map((a, i) => <ActionItem key={i} item={{ ...a }} />)}
                </>
              )}
              {result.action_items.long_term?.length > 0 && (
                <>
                  <div style={{ fontSize: 11, color: 'var(--green)', fontWeight: 600, margin: '12px 0 6px' }}>📅 LONG TERM</div>
                  {result.action_items.long_term.map((a, i) => <ActionItem key={i} item={a} />)}
                </>
              )}
            </Section>
          )}

          {/* Observability gaps */}
          {result.observability_gaps?.length > 0 && (
            <Section title="Observability gaps — what's missing" color="var(--purple)">
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                The following data was absent during this analysis. Without it, the above recommendations are based on architectural inference, not direct evidence.
              </div>
              {result.observability_gaps.map((g, i) => <GapItem key={i} gap={g} />)}
            </Section>
          )}

          {/* Automated remediation */}
          {result.automated_remediation?.length > 0 && (
            <Section title="Automated remediation triggers" color="var(--green)">
              {result.automated_remediation.map((r, i) => <RemediationItem key={i} r={r} />)}
            </Section>
          )}

          {/* Caveats */}
          {result.caveats?.length > 0 && (
            <div className="caveat-box" style={{ marginBottom: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--purple)' }}>⚠ Caveats</div>
              <ul style={{ paddingLeft: 16, lineHeight: 1.7 }}>
                {result.caveats.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}

          {/* Data needed */}
          {result.data_needed?.length > 0 && (
            <div className="info-box">
              <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--blue)' }}>📊 Data needed to improve this analysis</div>
              <ul style={{ paddingLeft: 16, lineHeight: 1.7, color: 'var(--text-secondary)' }}>
                {result.data_needed.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </div>
          )}

          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 16, textAlign: 'right' }}>
            Generated at {result.generated_at?.slice(0, 19).replace('T', ' ')} UTC
          </div>
        </div>
      </div>
    </div>
  )
}
