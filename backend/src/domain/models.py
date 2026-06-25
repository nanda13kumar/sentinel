"""
Domain models — pure Python dataclasses.
No framework imports. Swappable in any adapter.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SLOStatus(str, Enum):
    HEALTHY   = "healthy"
    AT_RISK   = "at_risk"
    BREACHED  = "breached"


class SLISeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class SLIPoint:
    timestamp: int
    value: float


@dataclass
class SLI:
    name: str
    display_name: str
    unit: str
    current_value: float
    target: float
    direction: str
    status: SLOStatus
    burn_rate_1h: float
    burn_rate_6h: float
    burn_rate_24h: float
    trend: list = field(default_factory=list)


@dataclass
class ErrorBudget:
    total_minutes: float
    allowed_downtime_minutes: float
    consumed_minutes: float
    remaining_minutes: float
    consumed_pct: float
    remaining_pct: float
    burn_rate_current: float
    projected_exhaustion_days: Optional[float]


@dataclass
class SLO:
    service_name: str
    sli_type: str
    target: float
    window_days: int
    current_compliance: float
    status: SLOStatus
    error_budget: ErrorBudget
    slis: list = field(default_factory=list)


@dataclass
class Incident:
    id: str
    service: str
    title: str
    severity: str
    root_cause: str
    impact: str
    started_at: str
    resolved_at: str
    duration_minutes: int
    availability_impact_pct: float


@dataclass
class SLATier:
    name: str
    tier: str
    target_pct: float
    actual_pct: float
    compliant: bool
    remaining_budget_minutes: float
    credits_owed_pct: float
    monthly_trend: list = field(default_factory=list)


@dataclass
class ServiceMetrics:
    name: str
    display_name: str
    description: str
    tech_stack: list
    tier: str
    avg_availability_pct: float
    avg_error_rate_pct: float
    avg_latency_p99_ms: float
    status: SLOStatus
    error_budget: ErrorBudget
    slos: list = field(default_factory=list)
    incidents: list = field(default_factory=list)
    daily_availability: dict = field(default_factory=dict)
    mttr_minutes: float = 0.0
    mtbf_days: float = 0.0


@dataclass
class DashboardSummary:
    generated_at: str
    window_days: int
    services: list
    sla_tiers: list
    overall_availability_pct: float
    total_incidents: int
    services_healthy: int
    services_at_risk: int
    services_breached: int


@dataclass
class AnalysisResult:
    service_name: str
    sli_type: str
    summary: str
    confidence: str
    root_cause_hypotheses: list
    action_items: dict
    observability_gaps: list
    automated_remediation: list
    caveats: list
    data_needed: list
    ai_model: str
    generated_at: str
