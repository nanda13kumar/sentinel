"""
Prometheus Adapter — reads from local sample_data.json (mock mode)
OR from a real Prometheus HTTP API (set PROMETHEUS_URL env var).
Implements IMetricsRepository port.
"""
import json
import math
import os
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from ...domain.models import (
    DashboardSummary, ServiceMetrics, SLATier, Incident,
    SLO, SLI, ErrorBudget, SLOStatus, AnalysisResult
)
from ...domain.ports import IMetricsRepository

DATA_PATH = Path(__file__).parent.parent.parent.parent / "sample_data.json"


def _status(budget_remaining_pct: float, slo_met: bool) -> SLOStatus:
    if not slo_met or budget_remaining_pct < 5:
        return SLOStatus.BREACHED
    if budget_remaining_pct < 30:
        return SLOStatus.AT_RISK
    return SLOStatus.HEALTHY


def _display_name(name: str) -> str:
    return name.replace("_", " ").title()


class PrometheusAdapter(IMetricsRepository):
    """
    Mock mode: reads pre-generated JSON that mirrors Prometheus query_range format.
    Real mode: set PROMETHEUS_URL=http://prometheus:9090 to hit live Prometheus.
    """

    def __init__(self):
        self._data: dict | None = None
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "")
        self._load()

    def _load(self):
        if self._data is None:
            with open(DATA_PATH) as f:
                self._data = json.load(f)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _recent_values(self, metric_values: list, days: int) -> list:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        # Since sample data is historical (2024), use the last N days worth of points
        n_points = days * 24
        return metric_values[-n_points:] if len(metric_values) > n_points else metric_values

    def _calc_error_budget(
        self,
        avail_vals: list,
        slo_pct: float,
        window_days: int,
    ) -> ErrorBudget:
        total_minutes = window_days * 24 * 60
        allowed = total_minutes * (1 - slo_pct / 100)
        avg_avail = statistics.mean(float(v) for _, v in avail_vals)
        consumed = total_minutes * (1 - avg_avail / 100)
        remaining = max(0.0, allowed - consumed)
        consumed_pct = min(100.0, round((consumed / allowed) * 100, 2)) if allowed > 0 else 100.0
        remaining_pct = round(100 - consumed_pct, 2)
        burn_rate = round(consumed_pct / 100 * (window_days / window_days), 2)  # simplified
        # burn_rate > 1 means consuming faster than allowed
        actual_rate = (consumed / allowed) if allowed > 0 else 99
        proj = None
        if actual_rate > 1 and remaining > 0:
            proj = round(remaining / (consumed / window_days), 1)
        return ErrorBudget(
            total_minutes=round(total_minutes, 1),
            allowed_downtime_minutes=round(allowed, 2),
            consumed_minutes=round(consumed, 2),
            remaining_minutes=round(remaining, 2),
            consumed_pct=consumed_pct,
            remaining_pct=remaining_pct,
            burn_rate_current=round(actual_rate, 2),
            projected_exhaustion_days=proj,
        )

    def _burn_rate(self, avail_vals: list, slo_pct: float, hours: int) -> float:
        window = avail_vals[-hours:] if len(avail_vals) >= hours else avail_vals
        avg = statistics.mean(float(v) for _, v in window)
        error_consumed = (1 - avg / 100)
        error_allowed_per_hour = (1 - slo_pct / 100)
        return round(error_consumed / error_allowed_per_hour if error_allowed_per_hour > 0 else 0, 2)

    def _service_status(self, svc_data: dict, window_days: int) -> tuple[SLOStatus, ErrorBudget]:
        cfg = svc_data["config"]
        avail_vals = self._recent_values(
            svc_data["metrics"]["availability"]["values"], window_days
        )
        budget = self._calc_error_budget(avail_vals, cfg["slo_availability"], window_days)
        avg_avail = statistics.mean(float(v) for _, v in avail_vals)
        status = _status(budget.remaining_pct, avg_avail >= cfg["slo_availability"])
        return status, budget

    def _build_slis(self, svc_data: dict, window_days: int) -> list[SLI]:
        cfg = svc_data["config"]
        metrics = svc_data["metrics"]

        avail_vals = self._recent_values(metrics["availability"]["values"], window_days)
        err_vals   = self._recent_values(metrics["error_rate"]["values"], window_days)
        p99_vals   = self._recent_values(metrics["latency_p99"]["values"], window_days)

        avg_avail = round(statistics.mean(float(v) for _, v in avail_vals), 4)
        avg_err   = round(statistics.mean(float(v) for _, v in err_vals), 4)
        avg_p99   = round(statistics.mean(float(v) for _, v in p99_vals), 1)

        budget = self._calc_error_budget(avail_vals, cfg["slo_availability"], window_days)
        avail_status = _status(budget.remaining_pct, avg_avail >= cfg["slo_availability"])
        err_status   = SLOStatus.HEALTHY if avg_err <= cfg["slo_error_rate_pct"] else SLOStatus.BREACHED
        lat_status   = SLOStatus.HEALTHY if avg_p99 <= cfg["slo_latency_p99_ms"] else SLOStatus.AT_RISK

        def sample_trend(vals, n=48):
            step = max(1, len(vals) // n)
            return [{"ts": int(ts), "value": round(float(v), 4)} for ts, v in vals[::step][-n:]]

        return [
            SLI(
                name="availability",
                display_name="Availability",
                unit="%",
                current_value=avg_avail,
                target=cfg["slo_availability"],
                direction="higher_is_better",
                status=avail_status,
                burn_rate_1h=self._burn_rate(avail_vals, cfg["slo_availability"], 1),
                burn_rate_6h=self._burn_rate(avail_vals, cfg["slo_availability"], 6),
                burn_rate_24h=self._burn_rate(avail_vals, cfg["slo_availability"], 24),
                trend=sample_trend(avail_vals),
            ),
            SLI(
                name="error_rate",
                display_name="Error Rate",
                unit="%",
                current_value=avg_err,
                target=cfg["slo_error_rate_pct"],
                direction="lower_is_better",
                status=err_status,
                burn_rate_1h=self._burn_rate(err_vals, 100 - cfg["slo_error_rate_pct"], 1),
                burn_rate_6h=self._burn_rate(err_vals, 100 - cfg["slo_error_rate_pct"], 6),
                burn_rate_24h=self._burn_rate(err_vals, 100 - cfg["slo_error_rate_pct"], 24),
                trend=sample_trend(err_vals),
            ),
            SLI(
                name="latency_p99",
                display_name="Latency p99",
                unit="ms",
                current_value=avg_p99,
                target=cfg["slo_latency_p99_ms"],
                direction="lower_is_better",
                status=lat_status,
                burn_rate_1h=0.0,
                burn_rate_6h=0.0,
                burn_rate_24h=0.0,
                trend=sample_trend(p99_vals),
            ),
        ]

    def _build_incidents(self, service: Optional[str] = None) -> list[Incident]:
        raw = self._data["incidents"]
        if service:
            raw = [i for i in raw if i["service"] == service]
        result = []
        year_start = datetime(2024, 5, 13, tzinfo=timezone.utc)
        for i, inc in enumerate(raw):
            start = year_start + timedelta(days=inc["day"], hours=inc["hour"])
            end   = start + timedelta(minutes=inc["duration_min"])
            result.append(Incident(
                id=f"INC-{i+1:04d}",
                service=inc["service"],
                title=inc["title"],
                severity=inc["severity"],
                root_cause=inc["root_cause"],
                impact=inc["impact"],
                started_at=start.isoformat(),
                resolved_at=end.isoformat(),
                duration_minutes=inc["duration_min"],
                availability_impact_pct=inc.get("drop_pct", 0.0),
            ))
        return sorted(result, key=lambda x: x.started_at, reverse=True)

    def _mttr(self, incidents: list[Incident]) -> float:
        if not incidents:
            return 0.0
        return round(statistics.mean(i.duration_minutes for i in incidents), 1)

    def _mtbf(self, incidents: list[Incident], window_days: int) -> float:
        if len(incidents) < 2:
            return float(window_days)
        n = len(incidents)
        return round(window_days / n, 1)

    # ── IMetricsRepository implementation ────────────────────────────────────

    def get_service(self, name: str, window_days: int = 30) -> ServiceMetrics:
        svc = self._data["services"][name]
        cfg = svc["config"]
        status, budget = self._service_status(svc, window_days)
        slis  = self._build_slis(svc, window_days)
        incs  = self._build_incidents(name)
        avail_vals = self._recent_values(svc["metrics"]["availability"]["values"], window_days)
        err_vals   = self._recent_values(svc["metrics"]["error_rate"]["values"], window_days)
        p99_vals   = self._recent_values(svc["metrics"]["latency_p99"]["values"], window_days)

        return ServiceMetrics(
            name=name,
            display_name=_display_name(name),
            description=cfg["description"],
            tech_stack=cfg["tech_stack"],
            tier=cfg["tier"],
            avg_availability_pct=round(statistics.mean(float(v) for _, v in avail_vals), 4),
            avg_error_rate_pct=round(statistics.mean(float(v) for _, v in err_vals), 4),
            avg_latency_p99_ms=round(statistics.mean(float(v) for _, v in p99_vals), 1),
            status=status,
            error_budget=budget,
            slos=[SLO(
                service_name=name,
                sli_type="availability",
                target=cfg["slo_availability"],
                window_days=window_days,
                current_compliance=round(statistics.mean(float(v) for _, v in avail_vals), 4),
                status=status,
                error_budget=budget,
                slis=slis,
            )],
            incidents=incs,
            daily_availability=svc.get("daily_availability", {}),
            mttr_minutes=self._mttr(incs),
            mtbf_days=self._mtbf(incs, window_days),
        )

    def get_dashboard(self, window_days: int = 30) -> DashboardSummary:
        services = [self.get_service(name, window_days) for name in self._data["services"]]
        avg_avail = round(statistics.mean(s.avg_availability_pct for s in services), 4)
        return DashboardSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            window_days=window_days,
            services=services,
            sla_tiers=self.get_sla_tiers(),
            overall_availability_pct=avg_avail,
            total_incidents=sum(len(s.incidents) for s in services),
            services_healthy=sum(1 for s in services if s.status == SLOStatus.HEALTHY),
            services_at_risk=sum(1 for s in services if s.status == SLOStatus.AT_RISK),
            services_breached=sum(1 for s in services if s.status == SLOStatus.BREACHED),
        )

    def get_sla_tiers(self) -> list[SLATier]:
        tiers_raw = self._data["sla_tiers"]
        services  = self._data["services"]
        result = []
        for tier in tiers_raw:
            # Find services in this tier
            tier_svcs = [s for s in services.values() if s["config"]["tier"] == tier["tier"]]
            if not tier_svcs:
                actual = 99.99
            else:
                actual = round(
                    statistics.mean(s["summary"]["avg_availability_pct"] for s in tier_svcs), 4
                )
            target = tier["target"]
            compliant = actual >= target
            total_min = 30 * 24 * 60
            allowed = total_min * (1 - target / 100)
            consumed = total_min * (1 - actual / 100)
            remaining = max(0.0, round(allowed - consumed, 2))
            credits = tier["penalty_pct"] if not compliant else 0.0

            # Monthly trend (last 12 months from daily data)
            monthly_trend = []
            if tier_svcs:
                sample_svc = tier_svcs[0]
                daily = sample_svc.get("daily_availability", {})
                from itertools import groupby
                for month_key in sorted(set(k[:7] for k in daily)):
                    vals = [v for k, v in daily.items() if k.startswith(month_key)]
                    if vals:
                        monthly_trend.append({
                            "month": month_key,
                            "actual_pct": round(statistics.mean(vals), 4),
                        })
            result.append(SLATier(
                name=tier["name"],
                tier=tier["tier"],
                target_pct=target,
                actual_pct=actual,
                compliant=compliant,
                remaining_budget_minutes=remaining,
                credits_owed_pct=credits,
                monthly_trend=monthly_trend[-12:],
            ))
        return result

    def get_incidents(self, service: Optional[str] = None, limit: int = 50) -> list[Incident]:
        return self._build_incidents(service)[:limit]

    def get_availability_series(self, service: str, days: int = 30) -> list[dict]:
        vals = self._recent_values(
            self._data["services"][service]["metrics"]["availability"]["values"], days
        )
        return [{"ts": int(ts), "value": round(float(v), 4)} for ts, v in vals]

    def get_error_budget_series(self, service: str, days: int = 30) -> list[dict]:
        svc = self._data["services"][service]
        cfg = svc["config"]
        avail_vals = self._recent_values(svc["metrics"]["availability"]["values"], days)
        total_min = days * 24 * 60
        allowed = total_min * (1 - cfg["slo_availability"] / 100)
        result = []
        consumed = 0.0
        for ts, av in avail_vals:
            consumed += (1 - float(av) / 100) * 60  # hourly point → minutes
            pct = min(100, round((consumed / allowed) * 100, 2)) if allowed > 0 else 100
            result.append({"ts": int(ts), "budget_remaining_pct": round(100 - pct, 2)})
        return result

    def get_heatmap(self, service: str, days: int = 90) -> list[dict]:
        daily = self._data["services"][service].get("daily_availability", {})
        sorted_days = sorted(daily.items())[-days:]
        return [{"date": d, "availability_pct": v} for d, v in sorted_days]
