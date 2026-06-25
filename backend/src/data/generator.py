"""
Generate 90 days of realistic Prometheus-style time-series data for 16 services.
Output schema matches exactly what prometheus_adapter.py expects.
"""
import json
import math
import random
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

WINDOW_START = datetime(2025, 3, 27, 0, 0, 0, tzinfo=timezone.utc)
WINDOW_END   = datetime(2025, 6, 24, 23, 0, 0, tzinfo=timezone.utc)  # 90 days
STEP_SECONDS = 3600

SERVICES = [
    # ── Enterprise (Tier 1) ───────────────────────────────────────────────────
    {
        "name": "api_gateway",
        "display_name": "API Gateway",
        "description": "Edge proxy routing all inbound traffic; handles TLS termination, rate limiting and WAF",
        "tech_stack": ["nginx", "envoy", "aws-alb", "terraform"],
        "tier": "Enterprise (Tier 1)",
        "slo_availability": 99.95, "slo_error_rate_pct": 0.05, "slo_latency_p99_ms": 250,
        "base_availability": 99.97, "base_error_rate": 0.03, "base_latency_p99": 180, "base_rps": 850,
    },
    {
        "name": "auth_service",
        "display_name": "Auth Service",
        "description": "JWT issuance, OIDC federation and session management",
        "tech_stack": ["python", "fastapi", "redis", "postgresql", "eks"],
        "tier": "Enterprise (Tier 1)",
        "slo_availability": 99.90, "slo_error_rate_pct": 0.10, "slo_latency_p99_ms": 200,
        "base_availability": 99.92, "base_error_rate": 0.08, "base_latency_p99": 140, "base_rps": 340,
    },
    {
        "name": "payment_processor",
        "display_name": "Payment Processor",
        "description": "PCI-DSS compliant payment processing with Stripe and Braintree integrations",
        "tech_stack": ["java", "spring-boot", "postgresql", "stripe", "vault"],
        "tier": "Enterprise (Tier 1)",
        "slo_availability": 99.95, "slo_error_rate_pct": 0.05, "slo_latency_p99_ms": 500,
        "base_availability": 99.96, "base_error_rate": 0.04, "base_latency_p99": 380, "base_rps": 55,
    },
    {
        "name": "billing_api",
        "display_name": "Billing API",
        "description": "Subscription billing, invoice generation and customer payment history",
        "tech_stack": ["node.js", "express", "postgresql", "stripe", "eks"],
        "tier": "Enterprise (Tier 1)",
        "slo_availability": 99.90, "slo_error_rate_pct": 0.10, "slo_latency_p99_ms": 400,
        "base_availability": 99.85, "base_error_rate": 0.15, "base_latency_p99": 310, "base_rps": 40,
    },
    # ── Business (Tier 2) ─────────────────────────────────────────────────────
    {
        "name": "user_service",
        "display_name": "User Service",
        "description": "User profile management, preferences and account settings",
        "tech_stack": ["go", "postgresql", "redis", "grpc"],
        "tier": "Business (Tier 2)",
        "slo_availability": 99.90, "slo_error_rate_pct": 0.20, "slo_latency_p99_ms": 300,
        "base_availability": 99.93, "base_error_rate": 0.12, "base_latency_p99": 220, "base_rps": 420,
    },
    {
        "name": "order_service",
        "display_name": "Order Service",
        "description": "Order lifecycle management from creation to fulfilment and returns",
        "tech_stack": ["python", "django", "postgresql", "celery", "redis"],
        "tier": "Business (Tier 2)",
        "slo_availability": 99.80, "slo_error_rate_pct": 0.20, "slo_latency_p99_ms": 600,
        "base_availability": 99.84, "base_error_rate": 0.18, "base_latency_p99": 480, "base_rps": 120,
    },
    {
        "name": "notification_service",
        "display_name": "Notification Service",
        "description": "Multi-channel delivery engine for email, SMS, push and in-app notifications",
        "tech_stack": ["node.js", "rabbitmq", "sendgrid", "twilio", "firebase"],
        "tier": "Business (Tier 2)",
        "slo_availability": 99.50, "slo_error_rate_pct": 0.50, "slo_latency_p99_ms": 2000,
        "base_availability": 99.70, "base_error_rate": 0.35, "base_latency_p99": 1400, "base_rps": 280,
    },
    {
        "name": "search_service",
        "display_name": "Search Service",
        "description": "Full-text and faceted search backed by Elasticsearch with ML-based ranking",
        "tech_stack": ["python", "elasticsearch", "redis", "fastapi"],
        "tier": "Business (Tier 2)",
        "slo_availability": 99.80, "slo_error_rate_pct": 0.20, "slo_latency_p99_ms": 500,
        "base_availability": 99.85, "base_error_rate": 0.15, "base_latency_p99": 390, "base_rps": 310,
    },
    # ── Starter (Tier 3) ──────────────────────────────────────────────────────
    {
        "name": "inventory_service",
        "display_name": "Inventory Service",
        "description": "Real-time stock tracking, warehouse sync and low-stock alerting",
        "tech_stack": ["rust", "postgresql", "kafka", "grpc"],
        "tier": "Starter (Tier 3)",
        "slo_availability": 99.50, "slo_error_rate_pct": 0.50, "slo_latency_p99_ms": 800,
        "base_availability": 99.60, "base_error_rate": 0.40, "base_latency_p99": 640, "base_rps": 65,
    },
    {
        "name": "analytics_service",
        "display_name": "Analytics Service",
        "description": "Business intelligence aggregations, funnel analysis and cohort reports",
        "tech_stack": ["python", "spark", "bigquery", "dbt", "airflow"],
        "tier": "Starter (Tier 3)",
        "slo_availability": 99.00, "slo_error_rate_pct": 1.00, "slo_latency_p99_ms": 5000,
        "base_availability": 99.20, "base_error_rate": 0.75, "base_latency_p99": 3800, "base_rps": 30,
    },
    {
        "name": "config_service",
        "display_name": "Config Service",
        "description": "Feature flag management, remote configuration and A/B test allocation",
        "tech_stack": ["go", "etcd", "grpc", "kubernetes"],
        "tier": "Starter (Tier 3)",
        "slo_availability": 99.90, "slo_error_rate_pct": 0.10, "slo_latency_p99_ms": 100,
        "base_availability": 99.94, "base_error_rate": 0.06, "base_latency_p99": 75, "base_rps": 1200,
    },
    {
        "name": "event_bus",
        "display_name": "Event Bus",
        "description": "Central Kafka-backed streaming platform for service-to-service async messaging",
        "tech_stack": ["kafka", "zookeeper", "schema-registry", "kafka-connect"],
        "tier": "Starter (Tier 3)",
        "slo_availability": 99.50, "slo_error_rate_pct": 0.50, "slo_latency_p99_ms": 150,
        "base_availability": 99.65, "base_error_rate": 0.35, "base_latency_p99": 110, "base_rps": 640,
    },
    # ── Internal / SRE ────────────────────────────────────────────────────────
    {
        "name": "data_pipeline",
        "display_name": "Data Pipeline",
        "description": "Kafka-backed ETL processing for analytics and downstream reporting",
        "tech_stack": ["python", "kafka", "spark", "s3", "airflow"],
        "tier": "Internal / SRE",
        "slo_availability": 99.00, "slo_error_rate_pct": 1.00, "slo_latency_p99_ms": 5000,
        "base_availability": 99.40, "base_error_rate": 0.60, "base_latency_p99": 3200, "base_rps": 95,
    },
    {
        "name": "recommendation_engine",
        "display_name": "Recommendation Engine",
        "description": "Collaborative filtering and content-based ML model serving for personalisation",
        "tech_stack": ["python", "pytorch", "redis", "mlflow", "triton"],
        "tier": "Internal / SRE",
        "slo_availability": 99.00, "slo_error_rate_pct": 1.00, "slo_latency_p99_ms": 300,
        "base_availability": 99.15, "base_error_rate": 0.80, "base_latency_p99": 240, "base_rps": 180,
    },
    {
        "name": "cdn_edge",
        "display_name": "CDN Edge",
        "description": "Global edge caching for static assets, media streams and API responses",
        "tech_stack": ["cloudfront", "lambda@edge", "s3", "waf"],
        "tier": "Internal / SRE",
        "slo_availability": 99.95, "slo_error_rate_pct": 0.05, "slo_latency_p99_ms": 100,
        "base_availability": 99.97, "base_error_rate": 0.03, "base_latency_p99": 75, "base_rps": 2400,
    },
    {
        "name": "ml_inference",
        "display_name": "ML Inference",
        "description": "Low-latency model inference for fraud detection, risk scoring and content moderation",
        "tech_stack": ["python", "triton", "onnx", "nvidia-gpu", "kubernetes"],
        "tier": "Internal / SRE",
        "slo_availability": 99.50, "slo_error_rate_pct": 0.50, "slo_latency_p99_ms": 50,
        "base_availability": 99.60, "base_error_rate": 0.40, "base_latency_p99": 42, "base_rps": 520,
    },
]

SLA_TIERS = [
    {"tier": "Enterprise (Tier 1)", "name": "Enterprise SLA",  "target": 99.99, "penalty_pct": 15.0},
    {"tier": "Business (Tier 2)",   "name": "Business SLA",    "target": 99.90, "penalty_pct": 10.0},
    {"tier": "Starter (Tier 3)",    "name": "Starter SLA",     "target": 99.50, "penalty_pct": 5.0},
    {"tier": "Internal / SRE",      "name": "Internal Target", "target": 99.00, "penalty_pct": 0.0},
]

INCIDENTS = [
    {"service": "auth_service",          "day": 3,  "hour": 2,  "duration_min": 47,  "severity": "critical", "title": "JWT secret rotation cascade",                              "root_cause": "Uncoordinated key rotation didn't propagate to all replicas within TTL window; 401 storms hit all downstream callers.",                                         "impact": "availability_drop", "drop_pct": 14.2},
    {"service": "api_gateway",           "day": 7,  "hour": 9,  "duration_min": 18,  "severity": "medium",   "title": "DDoS false positive — Cloudflare rate-limit blocked users", "root_cause": "Marketing campaign drove 4× organic traffic spike; Cloudflare rate limit flagged the burst as DDoS; 429s returned for 18 min.",                              "impact": "availability_drop", "drop_pct": 5.1},
    {"service": "payment_processor",     "day": 12, "hour": 14, "duration_min": 31,  "severity": "critical", "title": "Stripe API regional timeout — checkout failures",            "root_cause": "Stripe EU regional incident; payment_processor had no circuit-breaker; synchronous timeout chain blocked all checkout requests.",                            "impact": "availability_drop", "drop_pct": 11.6},
    {"service": "data_pipeline",         "day": 15, "hour": 3,  "duration_min": 112, "severity": "high",     "title": "Kafka consumer group rebalance storm",                      "root_cause": "Kafka broker upgrade triggered continuous rebalance loops in 3 consumer groups; session.timeout.ms was too low for the rolling restart window.",               "impact": "latency_spike",     "drop_pct": 0},
    {"service": "order_service",         "day": 18, "hour": 16, "duration_min": 41,  "severity": "high",     "title": "PostgreSQL connection pool exhaustion — orders queued",     "root_cause": "Month-end invoice run doubled concurrent writes; PgBouncer pool_size=20 on node handling 180 RPS caused full connection starvation.",                         "impact": "availability_drop", "drop_pct": 9.0},
    {"service": "notification_service",  "day": 22, "hour": 11, "duration_min": 33,  "severity": "medium",   "title": "SendGrid daily quota exhausted — email delivery stalled",    "root_cause": "Triggered email campaign sent 2.1M emails; hit SendGrid 2M/day plan limit; excess notifications silently dropped without alerting on-call.",                "impact": "availability_drop", "drop_pct": 6.5},
    {"service": "search_service",        "day": 26, "hour": 7,  "duration_min": 55,  "severity": "high",     "title": "Elasticsearch heap pressure — GC pauses spiked query times",  "root_cause": "New ML ranking feature loaded an 8 GB model into ES heap; JVM GC pauses reached 15 s; all search queries timed out at p99.",                               "impact": "latency_spike",     "drop_pct": 0},
    {"service": "auth_service",          "day": 30, "hour": 4,  "duration_min": 24,  "severity": "high",     "title": "TLS certificate renewal failure — service unreachable",      "root_cause": "cert-manager ACME DNS-01 challenge failed due to stale IAM credentials for Route 53; certificate expired at 04:12 UTC.",                                    "impact": "availability_drop", "drop_pct": 6.1},
    {"service": "billing_api",           "day": 35, "hour": 23, "duration_min": 47,  "severity": "critical", "title": "Stripe webhook backlog — payments silently dropped",          "root_cause": "SQS dead-letter queue filled after Stripe retry storm; billing_api had no dead-letter handler; payment events were silently dropped.",                      "impact": "availability_drop", "drop_pct": 8.6},
    {"service": "recommendation_engine", "day": 38, "hour": 6,  "duration_min": 28,  "severity": "medium",   "title": "GPU OOM during nightly model retraining",                    "root_cause": "Expanded training dataset exceeded 24 GB GPU VRAM; training job OOMed and crashed inference workers sharing the same node.",                                 "impact": "availability_drop", "drop_pct": 7.3},
    {"service": "inventory_service",     "day": 42, "hour": 13, "duration_min": 19,  "severity": "medium",   "title": "Warehouse sync deadlock — stock levels stale",                "root_cause": "Concurrent bulk-write and replication lag triggered row-level deadlock; auto-vacuum had been disabled on the inventory table.",                               "impact": "availability_drop", "drop_pct": 4.2},
    {"service": "api_gateway",           "day": 46, "hour": 11, "duration_min": 55,  "severity": "medium",   "title": "WAF managed rule — false positive blocked POST /graphql",     "root_cause": "Managed WAF rule update; new SQLi rule triggered on valid multiline GraphQL queries; no canary deployment was used before the push.",                       "impact": "availability_drop", "drop_pct": 6.0},
    {"service": "user_service",          "day": 50, "hour": 8,  "duration_min": 22,  "severity": "low",      "title": "Redis cache stampede after hot key eviction",                 "root_cause": "Single hot user-preferences key expired under peak load; thundering herd hit PostgreSQL; took 22 min to fully re-prime the cache.",                          "impact": "latency_spike",     "drop_pct": 0},
    {"service": "ml_inference",          "day": 55, "hour": 1,  "duration_min": 38,  "severity": "high",     "title": "ONNX Runtime v1.18 regression — fraud model crash loop",      "root_cause": "ONNX Runtime v1.18 regression; TensorRT EP segfaulted on batch size > 64; inference pod crash-looped for 38 min until rolled back.",                       "impact": "availability_drop", "drop_pct": 12.5},
    {"service": "event_bus",             "day": 58, "hour": 5,  "duration_min": 33,  "severity": "medium",   "title": "Kafka partition rebalance — consumer lag spike",               "root_cause": "Rolling EKS node upgrade triggered Kafka rebalance; session.timeout.ms=6000 was too short for the rolling restart window.",                                "impact": "latency_spike",     "drop_pct": 0},
    {"service": "cdn_edge",              "day": 62, "hour": 17, "duration_min": 14,  "severity": "low",      "title": "CloudFront origin timeout — cache-miss storm on product launch","root_cause": "New product launch cache-busted all CDN edges simultaneously; origin received 40× normal traffic; p99 spiked for 14 min.",                                   "impact": "latency_spike",     "drop_pct": 0},
    {"service": "config_service",        "day": 65, "hour": 22, "duration_min": 9,   "severity": "low",      "title": "etcd leader election delay — feature flag reads stalled",     "root_cause": "etcd leader stepped down during quorum health check; re-election took 9 min; config reads timed out with 503s during the window.",                           "impact": "availability_drop", "drop_pct": 3.1},
    {"service": "analytics_service",     "day": 68, "hour": 3,  "duration_min": 201, "severity": "high",     "title": "BigQuery slot quota exceeded — daily batch failed",            "root_cause": "Unoptimised query scanned 4 TB without partition pruning; exceeded org slot quota; all batch jobs queued for 201 min until slots freed.",                    "impact": "latency_spike",     "drop_pct": 0},
    {"service": "payment_processor",     "day": 72, "hour": 15, "duration_min": 26,  "severity": "high",     "title": "Vault connection timeout — PCI token fetch failed",            "root_cause": "HashiCorp Vault auto-unseal on AWS KMS failed after IAM role rotation; PCI token fetches timed out; payment writes blocked for 26 min.",                   "impact": "availability_drop", "drop_pct": 10.3},
    {"service": "order_service",         "day": 76, "hour": 10, "duration_min": 44,  "severity": "medium",   "title": "Celery worker crash loop — async order processing stalled",   "root_cause": "Malformed order payload caused Celery worker OOM; supervisor entered restart loop; async processing queue backed up for 44 min before hotfix deployed.",     "impact": "availability_drop", "drop_pct": 5.8},
    {"service": "data_pipeline",         "day": 80, "hour": 2,  "duration_min": 62,  "severity": "low",      "title": "S3 PUT throttling during nightly batch — pipeline stall",      "root_cause": "Nightly batch hit S3 PUT rate limit (3500 req/s); all writes shared a single key prefix; exponential backoff ran for 62 min.",                               "impact": "latency_spike",     "drop_pct": 0},
    {"service": "notification_service",  "day": 83, "hour": 19, "duration_min": 51,  "severity": "high",     "title": "RabbitMQ memory alarm — all publishers blocked",               "root_cause": "Unacked messages grew to 2.1 M; RabbitMQ hit vm_memory_high_watermark=0.4; all publishers blocked for 51 min until consumer lag was cleared.",               "impact": "availability_drop", "drop_pct": 8.9},
    {"service": "search_service",        "day": 86, "hour": 7,  "duration_min": 37,  "severity": "medium",   "title": "Elasticsearch shard allocation failure — index read-only",     "root_cause": "Disk watermark breached on data node; Elasticsearch set all indices to read-only; all write requests returned 403 for 37 min.",                              "impact": "availability_drop", "drop_pct": 7.2},
    {"service": "billing_api",           "day": 89, "hour": 16, "duration_min": 41,  "severity": "critical", "title": "PostgreSQL connection pool exhaustion — billing writes failed",  "root_cause": "PgBouncer pool_size=20 for node handling 180 RPS; concurrent month-end processing caused full connection starvation for 41 min.",                            "impact": "availability_drop", "drop_pct": 11.0},
]


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
    lookup: dict = {s["name"]: [] for s in SERVICES}
    for inc in INCIDENTS:
        start_dt = WINDOW_START + timedelta(days=inc["day"], hours=inc["hour"])
        end_dt   = start_dt + timedelta(minutes=inc["duration_min"])
        lookup[inc["service"]].append((start_dt.timestamp(), end_dt.timestamp(), inc))
    return lookup


def availability_for_point(ts: float, service: str, incident_lookup: dict, noise_seed: float) -> float:
    base = 99.97 - random.gauss(0, 0.01)
    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e and inc["impact"] == "availability_drop":
            progress = (ts - s) / max(e - s, 1)
            factor = math.sin(progress * math.pi)
            base -= inc["drop_pct"] * factor
    return round(max(0.0, min(100.0, base + noise_seed * 0.03)), 4)


def latency_for_point(ts: float, service: str, hour: int, incident_lookup: dict, base_p99: int) -> dict:
    tf = hour_traffic_factor(hour)
    base_p50  = base_p99 * 0.25 * (0.8 + tf * 0.4)
    base_p95  = base_p99 * 0.65 * (0.9 + tf * 0.2)
    base_p99v = base_p99 * (0.85 + tf * 0.3)

    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e and inc["impact"] == "latency_spike":
            progress = (ts - s) / max(e - s, 1)
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


def error_rate_for_point(ts: float, service: str, incident_lookup: dict) -> float:
    base = random.gauss(0.02, 0.005)
    for (s, e, inc) in incident_lookup[service]:
        if s <= ts <= e:
            progress = (ts - s) / max(e - s, 1)
            factor = math.sin(progress * math.pi)
            if inc["impact"] == "availability_drop":
                base += inc["drop_pct"] * 0.08 * factor
            else:
                base += 0.3 * factor
    return round(max(0.0, min(100.0, base)), 4)


def request_rate_for_point(hour: int, weekday: int, base_rps: int) -> float:
    tf = hour_traffic_factor(hour)
    df = day_of_week_factor(weekday)
    return round(base_rps * tf * df * random.gauss(1.0, 0.04), 1)


def prometheus_metric(metric_name: str, labels: dict, values: list) -> dict:
    return {"metric": {"__name__": metric_name, **labels}, "values": values}


def generate() -> dict:
    print(f"Generating 90-day synthetic data for {len(SERVICES)} services...")
    incident_lookup = build_incident_lookup()

    all_timestamps: list = []
    ts = WINDOW_START.timestamp()
    while ts <= WINDOW_END.timestamp():
        all_timestamps.append(ts)
        ts += STEP_SECONDS

    print(f"  Time points: {len(all_timestamps)} per service ({len(all_timestamps) / 24:.0f} days)")

    output: dict = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "start": WINDOW_START.isoformat(),
            "end": WINDOW_END.isoformat(),
            "step_seconds": STEP_SECONDS,
            "total_points_per_service": len(all_timestamps),
            "services": [s["name"] for s in SERVICES],
        },
        "services": {},
        "incidents": INCIDENTS,
        "sla_tiers": SLA_TIERS,
    }

    _internal_keys = {"name", "base_rps", "base_availability", "base_error_rate", "base_latency_p99"}

    for cfg in SERVICES:
        name = cfg["name"]
        print(f"  {name}")
        avail_vals, lat_p50, lat_p95, lat_p99, err_vals, rps_vals = [], [], [], [], [], []
        noise_seeds = [random.gauss(0, 1) for _ in all_timestamps]

        for i, ts_val in enumerate(all_timestamps):
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)

            av  = availability_for_point(ts_val, name, incident_lookup, noise_seeds[i])
            lat = latency_for_point(ts_val, name, dt.hour, incident_lookup, cfg["slo_latency_p99_ms"])
            er  = error_rate_for_point(ts_val, name, incident_lookup)
            rps = request_rate_for_point(dt.hour, dt.weekday(), cfg["base_rps"])

            avail_vals.append([int(ts_val), str(av)])
            lat_p50.append([int(ts_val), str(lat["p50"])])
            lat_p95.append([int(ts_val), str(lat["p95"])])
            lat_p99.append([int(ts_val), str(lat["p99"])])
            err_vals.append([int(ts_val), str(er)])
            rps_vals.append([int(ts_val), str(rps)])

        av_nums  = [float(v[1]) for v in avail_vals]
        er_nums  = [float(v[1]) for v in err_vals]
        p99_nums = [float(v[1]) for v in lat_p99]

        avg_avail = round(statistics.mean(av_nums), 4)
        avg_error = round(statistics.mean(er_nums), 4)
        avg_p99   = round(statistics.mean(p99_nums), 1)

        total_min   = len(all_timestamps) * 60
        slo_avail   = cfg["slo_availability"]
        allowed_min = total_min * (1 - slo_avail / 100)
        actual_min  = total_min * (1 - avg_avail / 100)
        budget_used = round(min(100.0, (actual_min / allowed_min) * 100), 2) if allowed_min > 0 else 100.0
        budget_left = round(100 - budget_used, 2)

        output["services"][name] = {
            "config": {k: v for k, v in cfg.items() if k not in _internal_keys},
            "summary": {
                "avg_availability_pct":       avg_avail,
                "avg_error_rate_pct":         avg_error,
                "avg_latency_p99_ms":         avg_p99,
                "slo_availability_met":       avg_avail >= slo_avail,
                "slo_error_rate_met":         avg_error <= cfg["slo_error_rate_pct"],
                "slo_latency_met":            avg_p99   <= cfg["slo_latency_p99_ms"],
                "error_budget_used_pct":      budget_used,
                "error_budget_remaining_pct": budget_left,
                "total_incidents": sum(1 for inc in INCIDENTS if inc["service"] == name),
            },
            "metrics": {
                "availability": prometheus_metric("service_availability_percent", {"service": name, "env": "prod"}, avail_vals),
                "latency_p50":  prometheus_metric("http_request_duration_ms",     {"service": name, "quantile": "0.5",  "env": "prod"}, lat_p50),
                "latency_p95":  prometheus_metric("http_request_duration_ms",     {"service": name, "quantile": "0.95", "env": "prod"}, lat_p95),
                "latency_p99":  prometheus_metric("http_request_duration_ms",     {"service": name, "quantile": "0.99", "env": "prod"}, lat_p99),
                "error_rate":   prometheus_metric("http_error_rate_percent",      {"service": name, "env": "prod"}, err_vals),
                "request_rate": prometheus_metric("http_requests_per_second",     {"service": name, "env": "prod"}, rps_vals),
            },
        }

    print("  Computing daily availability aggregates...")
    for svc_cfg in SERVICES:
        name = svc_cfg["name"]
        daily: dict = {}
        for ts_val, val in output["services"][name]["metrics"]["availability"]["values"]:
            day_key = datetime.fromtimestamp(ts_val, tz=timezone.utc).strftime("%Y-%m-%d")
            daily.setdefault(day_key, []).append(float(val))
        output["services"][name]["daily_availability"] = {
            day: round(sum(vals) / len(vals), 4) for day, vals in sorted(daily.items())
        }

    print(f"Done — {len(SERVICES)} services × {len(all_timestamps)} points each.")
    return output


if __name__ == "__main__":
    out_path = Path(__file__).parent.parent.parent / "sample_data.json"
    data = generate()
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"Written → {out_path} ({size_mb:.2f} MB)")
