"""
Sentinel — 1-Year Synthetic Prometheus Data Generator
Generates realistic SLI/SLO metrics for 4 services with incidents, seasonality,
and correlated degradations. Output mimics Prometheus HTTP API query_range format.
"""
import json
import math
import random
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

random.seed(42)

# ─── Configuration ────────────────────────────────────────────────────────────

SERVICES = {
    "api_gateway": {
        "slo_availability": 99.9,
        "slo_latency_p99_ms": 300,
        "slo_error_rate_pct": 0.1,
        "tier": "enterprise",
        "description": "Public-facing API gateway routing traffic to all downstream services",
        "tech_stack": ["AWS ALB", "Kong", "Node.js", "Redis"],
        "replicas": 6,
    },
    "auth_service": {
        "slo_availability": 99.9,
        "slo_latency_p99_ms": 200,
        "slo_error_rate_pct": 0.1,
        "tier": "enterprise",
        "description": "JWT-based authentication and authorisation service",
        "tech_stack": ["Python FastAPI", "PostgreSQL", "Redis", "AWS KMS"],
        "replicas": 3,
    },
    "data_pipeline": {
        "slo_availability": 99.5,
        "slo_latency_p99_ms": 2000,
        "slo_error_rate_pct": 0.5,
        "tier": "business",
        "description": "Kafka-based event streaming and ETL pipeline",
        "tech_stack": ["Apache Kafka", "Apache Spark", "AWS S3", "PostgreSQL"],
        "replicas": 4,
    },
    "billing_api": {
        "slo_availability": 99.9,
        "slo_latency_p99_ms": 500,
        "slo_error_rate_pct": 0.1,
        "tier": "enterprise",
        "description": "Stripe-integrated billing, invoicing and payment processing service",
        "tech_stack": ["Go", "PostgreSQL", "Stripe SDK", "AWS SQS"],
        "replicas": 2,
    },
}

SLA_TIERS = [
    {"name": "Enterprise", "tier": "enterprise", "target": 99.99, "penalty_pct": 20},
    {"name": "Business",   "tier": "business",   "target": 99.9,  "penalty_pct": 10},
    {"name": "Starter",    "tier": "starter",    "target": 99.5,  "penalty_pct": 5},
    {"name": "Internal",   "tier": "internal",   "target": 99.0,  "penalty_pct": 0},
]

# Realistic incidents — (service, start_offset_days_from_year_start, duration_minutes, severity, type, root_cause)
INCIDENTS = [
    {
        "service": "auth_service",
        "day": 15, "hour": 2, "duration_min": 47,
        "severity": "critical",
        "title": "JWT secret rotation cascade",
        "root_cause": "Uncoordinated secret rotation caused 401 storms across all downstream callers.",
        "impact": "availability_drop", "drop_pct": 14.2,
    },
    {
        "service": "data_pipeline",
        "day": 28, "hour": 14, "duration_min": 112,
        "severity": "high",
        "title": "Kafka consumer group rebalance storm",
        "root_cause": "Kafka broker upgrade triggered continuous rebalance loops in 3 consumer groups.",
        "impact": "latency_spike", "drop_pct": 0,
    },
    {
        "service": "billing_api",
        "day": 45, "hour": 23, "duration_min": 31,
        "severity": "critical",
        "title": "Stripe webhook backlog exhaustion",
        "root_cause": "SQS dead-letter queue filled after Stripe retry storm; payments silently dropped.",
        "impact": "availability_drop", "drop_pct": 8.6,
    },
    {
        "service": "api_gateway",
        "day": 72, "hour": 9, "duration_min": 18,
        "severity": "medium",
        "title": "Redis connection pool exhaustion",
        "root_cause": "Rate-limit counters accumulated idle connections exceeding pool max size.",
        "impact": "latency_spike", "drop_pct": 0,
    },
    {
        "service": "auth_service",
        "day": 98, "hour": 3, "duration_min": 24,
        "severity": "high",
        "title": "TLS certificate renewal failure",
        "root_cause": "cert-manager ACME challenge failed due to DNS propagation delay; service unreachable.",
        "impact": "availability_drop", "drop_pct": 6.1,
    },
    {
        "service": "data_pipeline",
        "day": 130, "hour": 11, "duration_min": 89,
        "severity": "high",
        "title": "S3 throttling — data ingestion stall",
        "root_cause": "Excessive GetObject requests hit S3 prefix-level throttle during batch reprocessing.",
        "impact": "latency_spike", "drop_pct": 0,
    },
    {
        "service": "billing_api",
        "day": 162, "hour": 16, "duration_min": 55,
        "severity": "critical",
        "title": "PostgreSQL connection pool exhaustion",
        "root_cause": "Deployment rollout kept old pods alive; doubled DB connections exhausted pool.",
        "impact": "availability_drop", "drop_pct": 11.3,
    },
    {
        "service": "api_gateway",
        "day": 195, "hour": 20, "duration_min": 9,
        "severity": "low",
        "title": "WAF rule misconfig — false positive block",
        "root_cause": "OWASP CRS rule 942100 blocked legitimate SQL-like query parameters.",
        "impact": "availability_drop", "drop_pct": 2.1,
    },
    {
        "service": "auth_service",
        "day": 228, "hour": 1, "duration_min": 38,
        "severity": "high",
        "title": "LDAP directory sync delay",
        "root_cause": "AD sync job failed silently; token validation fell through to stale cache.",
        "impact": "availability_drop", "drop_pct": 4.8,
    },
    {
        "service": "data_pipeline",
        "day": 265, "hour": 7, "duration_min": 201,
        "severity": "critical",
        "title": "Schema Registry disk full",
        "root_cause": "Uncompacted topics grew schema registry disk to 100%; all producers blocked.",
        "impact": "availability_drop", "drop_pct": 18.7,
    },
    {
        "service": "billing_api",
        "day": 298, "hour": 19, "duration_min": 44,
        "severity": "high",
        "title": "Tax API provider timeout cascade",
        "root_cause": "Third-party tax calculation API SLA breach caused synchronous timeout chain.",
        "impact": "latency_spike", "drop_pct": 0,
    },
    {
        "service": "api_gateway",
        "day": 340, "hour": 13, "duration_min": 7,
        "severity": "low",
        "title": "DDoS false positive — legitimate traffic blocked",
        "root_cause": "Rate-limit rule triggered on mobile SDK retry storm after app release.",
        "impact": "availability_drop", "drop_pct": 1.4,
    },
]

# ─── Generator ────────────────────────────────────────────────────────────────

YEAR_START = datetime(2024, 5, 13, 0, 0, 0, tzinfo=timezone.utc)
YEAR_END   = datetime(2025, 5, 12, 23, 59, 59, tzinfo=timezone.utc)
STEP_SECONDS = 3600  # 1h resolution


def hour_traffic_factor(hour: int) -> float:
    """Realistic traffic curve — low at night, peak midday/evening."""
    if 0 <= hour < 6:
        return 0.15 + 0.05 * math.sin(hour * math.pi / 6)
    elif 6 <= hour < 12:
        return 0.15 + 0.7 * ((hour - 6) / 6)
    elif 12 <= hour < 14:
        return 0.85 + 0.15 * math.sin((hour - 12) * math.pi / 2)
    elif 14 <= hour < 20:
        return 0.75 + 0.2 * math.sin((hour - 14) * math.pi / 6)
    else:
        return 0.8 - 0.6 * ((hour - 20) / 4)


def day_of_week_factor(weekday: int) -> float:
    return {0: 0.9, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.95, 5: 0.55, 6: 0.4}[weekday]


def build_incident_lookup() -> dict:
    """Return {service: [(start_ts, end_ts, incident_dict)]}"""
    lookup: dict = {s: [] for s in SERVICES}
    for inc in INCIDENTS:
        start_dt = YEAR_START + timedelta(days=inc["day"], hours=inc["hour"])
        end_dt   = start_dt + timedelta(minutes=inc["duration_min"])
        lookup[inc["service"]].append((start_dt.timestamp(), end_dt.timestamp(), inc))
    return lookup


def availability_for_point(
    ts: float,
    service: str,
    incident_lookup: dict,
    noise_seed: float,
) -> float:
    base = 99.97 - random.gauss(0, 0.01)
    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e and inc["impact"] == "availability_drop":
            progress = (ts - s) / (e - s)
            factor = math.sin(progress * math.pi)  # bell curve within incident
            base -= inc["drop_pct"] * factor
    return round(max(0.0, min(100.0, base + noise_seed * 0.03)), 4)


def latency_for_point(
    ts: float,
    service: str,
    hour: int,
    incident_lookup: dict,
    base_p99: int,
) -> dict:
    tf = hour_traffic_factor(hour)
    base_p50  = base_p99 * 0.25 * (0.8 + tf * 0.4)
    base_p95  = base_p99 * 0.65 * (0.9 + tf * 0.2)
    base_p99v = base_p99 * (0.85 + tf * 0.3)

    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e and inc["impact"] == "latency_spike":
            progress = (ts - s) / (e - s)
            factor = math.sin(progress * math.pi)
            spike = 3.5 * factor
            base_p50  *= (1 + spike * 0.5)
            base_p95  *= (1 + spike * 0.8)
            base_p99v *= (1 + spike * 1.2)

    noise = random.gauss(1.0, 0.05)
    return {
        "p50": round(base_p50 * noise, 1),
        "p95": round(base_p95 * noise, 1),
        "p99": round(base_p99v * noise, 1),
    }


def error_rate_for_point(
    ts: float,
    service: str,
    incident_lookup: dict,
) -> float:
    base = random.gauss(0.02, 0.005)
    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e:
            progress = (ts - s) / (e - s)
            factor = math.sin(progress * math.pi)
            if inc["impact"] == "availability_drop":
                base += inc["drop_pct"] * 0.08 * factor
            else:
                base += 0.3 * factor
    return round(max(0.0, min(100.0, base)), 4)


def request_rate_for_point(hour: int, weekday: int, service: str) -> float:
    base_rps = {"api_gateway": 450, "auth_service": 180, "data_pipeline": 95, "billing_api": 40}
    tf = hour_traffic_factor(hour)
    df = day_of_week_factor(weekday)
    return round(base_rps[service] * tf * df * random.gauss(1.0, 0.04), 1)


def prometheus_metric(metric_name: str, labels: dict, values: list) -> dict:
    """Wrap values in Prometheus query_range API format."""
    return {
        "metric": {"__name__": metric_name, **labels},
        "values": values,  # [[timestamp, "value"], ...]
    }


def generate() -> dict:
    print("Generating 1-year synthetic Prometheus data...")
    incident_lookup = build_incident_lookup()

    all_timestamps = []
    ts = YEAR_START.timestamp()
    end_ts = YEAR_END.timestamp()
    while ts <= end_ts:
        all_timestamps.append(ts)
        ts += STEP_SECONDS

    print(f"  Timestamps: {len(all_timestamps)} hourly points per service")

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "start": YEAR_START.isoformat(),
            "end": YEAR_END.isoformat(),
            "step_seconds": STEP_SECONDS,
            "total_points_per_service": len(all_timestamps),
            "services": list(SERVICES.keys()),
        },
        "services": {},
        "incidents": INCIDENTS,
        "sla_tiers": SLA_TIERS,
    }

    for service, cfg in SERVICES.items():
        print(f"  Generating: {service}")
        avail_vals, lat_p50, lat_p95, lat_p99, err_vals, rps_vals = [], [], [], [], [], []
        noise_seeds = [random.gauss(0, 1) for _ in all_timestamps]

        for i, ts_val in enumerate(all_timestamps):
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
            hour = dt.hour
            weekday = dt.weekday()
            ts_str = str(int(ts_val))

            av = availability_for_point(ts_val, service, incident_lookup, noise_seeds[i])
            lat = latency_for_point(ts_val, service, hour, incident_lookup, cfg["slo_latency_p99_ms"])
            er = error_rate_for_point(ts_val, service, incident_lookup)
            rps = request_rate_for_point(hour, weekday, service)

            avail_vals.append([int(ts_val), str(av)])
            lat_p50.append([int(ts_val), str(lat["p50"])])
            lat_p95.append([int(ts_val), str(lat["p95"])])
            lat_p99.append([int(ts_val), str(lat["p99"])])
            err_vals.append([int(ts_val), str(er)])
            rps_vals.append([int(ts_val), str(rps)])

        # Compute derived stats
        av_nums = [float(v[1]) for v in avail_vals]
        er_nums = [float(v[1]) for v in err_vals]
        p99_nums = [float(v[1]) for v in lat_p99]

        avg_avail = round(sum(av_nums) / len(av_nums), 4)
        avg_error = round(sum(er_nums) / len(er_nums), 4)
        avg_p99   = round(sum(p99_nums) / len(p99_nums), 1)

        total_minutes = len(all_timestamps) * 60
        slo_avail = cfg["slo_availability"]
        allowed_downtime_min = total_minutes * (1 - slo_avail / 100)
        actual_downtime_min  = total_minutes * (1 - avg_avail / 100)
        budget_used_pct = round(min(100, (actual_downtime_min / allowed_downtime_min) * 100), 2) if allowed_downtime_min > 0 else 100
        budget_remaining_pct = round(100 - budget_used_pct, 2)

        output["services"][service] = {
            "config": cfg,
            "summary": {
                "avg_availability_pct": avg_avail,
                "avg_error_rate_pct": avg_error,
                "avg_latency_p99_ms": avg_p99,
                "slo_availability_met": avg_avail >= slo_avail,
                "slo_error_rate_met": avg_error <= cfg["slo_error_rate_pct"],
                "slo_latency_met": avg_p99 <= cfg["slo_latency_p99_ms"],
                "error_budget_used_pct": budget_used_pct,
                "error_budget_remaining_pct": budget_remaining_pct,
                "total_incidents": sum(1 for inc in INCIDENTS if inc["service"] == service),
            },
            "metrics": {
                "availability": prometheus_metric(
                    "service_availability_percent",
                    {"service": service, "env": "prod"},
                    avail_vals,
                ),
                "latency_p50": prometheus_metric(
                    "http_request_duration_ms",
                    {"service": service, "quantile": "0.5", "env": "prod"},
                    lat_p50,
                ),
                "latency_p95": prometheus_metric(
                    "http_request_duration_ms",
                    {"service": service, "quantile": "0.95", "env": "prod"},
                    lat_p95,
                ),
                "latency_p99": prometheus_metric(
                    "http_request_duration_ms",
                    {"service": service, "quantile": "0.99", "env": "prod"},
                    lat_p99,
                ),
                "error_rate": prometheus_metric(
                    "http_error_rate_percent",
                    {"service": service, "env": "prod"},
                    err_vals,
                ),
                "request_rate": prometheus_metric(
                    "http_requests_per_second",
                    {"service": service, "env": "prod"},
                    rps_vals,
                ),
            },
        }

    # Compute daily availability for heatmap (last 90 days)
    print("  Computing daily aggregates...")
    for service in SERVICES:
        av_vals = output["services"][service]["metrics"]["availability"]["values"]
        daily = {}
        for ts_val, val in av_vals:
            day_key = datetime.fromtimestamp(ts_val, tz=timezone.utc).strftime("%Y-%m-%d")
            daily.setdefault(day_key, []).append(float(val))
        output["services"][service]["daily_availability"] = {
            day: round(sum(vals) / len(vals), 4) for day, vals in sorted(daily.items())
        }

    print(f"Done. {len(SERVICES)} services × {len(all_timestamps)} points each.")
    return output


if __name__ == "__main__":
    out_path = Path(__file__).parent / "sample_data.json"
    data = generate()
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"Written to {out_path} ({size_mb:.2f} MB)")
