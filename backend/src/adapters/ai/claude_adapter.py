"""
Claude AI Adapter — implements IAIAnalyzer port.
Sends rich context (metrics, incidents, simulated arch/logs) to Claude Sonnet
and returns structured AnalysisResult with actionable recommendations.
"""
import json
import os
from datetime import datetime, timezone

import httpx

from ...domain.models import ServiceMetrics, Incident, AnalysisResult, SLOStatus
from ...domain.ports import IAIAnalyzer

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

# Simulated architecture context per service (in real Sentinel, pull from Terraform/GitHub)
SIMULATED_ARCH = {
    "api_gateway": """
Terraform-managed infrastructure:
- 6x Kong gateway pods (EKS, t3.medium) behind AWS ALB
- Redis 7.x (ElastiCache, r6g.large) for rate-limit counters
- WAF: AWS WAF v2 with OWASP Core Rule Set 3.3
- Autoscaling: HPA min=3 max=10, CPU threshold 70%
- Upstream timeout: 30s; retry policy: 2 retries on 5xx
Known architecture gaps:
- No circuit breaker between gateway and auth_service
- WAF rules not tuned for internal API traffic patterns
- Redis eviction policy: allkeys-lru (may silently drop rate-limit state)
""",
    "auth_service": """
Terraform-managed infrastructure:
- 3x FastAPI pods (EKS, t3.small) — single AZ deployment
- PostgreSQL 14 (RDS, db.t3.medium, Multi-AZ disabled)
- Redis 7.x (ElastiCache) for token caching, TTL=15m
- AWS KMS for JWT signing key management
- Secret Manager rotation: 30-day schedule (cert-manager for TLS)
Known architecture gaps:
- Single AZ → entire auth service fails on AZ event
- No connection pooling (PgBouncer not deployed)
- JWT signing key rotation not zero-downtime (brief 401 storms)
- Thread dumps NOT configured; no async profiler attached
- Missing: distributed tracing (no OpenTelemetry instrumentation)
""",
    "data_pipeline": """
Terraform-managed infrastructure:
- Apache Kafka 3.5 (MSK, 3 brokers, kafka.m5.large)
- Apache Spark 3.4 (EMR Serverless) for batch ETL
- Schema Registry (Confluent, self-managed on EC2 t3.medium)
- AWS S3 (data lake) + PostgreSQL (RDS, db.m5.large) for metadata
- Consumer groups: 4 active groups, avg lag monitored via Kafka Exporter
Known architecture gaps:
- Schema Registry on single EC2 — no HA, disk not auto-expanded
- No dead-letter topic for failed consumer messages
- S3 prefix design: date-partitioned (hot prefix = throttle risk)
- Kafka retention: 7 days (schema registry segments not compacted)
- Heap dumps NOT collected on OOM; no GC pause metrics exported
""",
    "billing_api": """
Terraform-managed infrastructure:
- 2x Go service pods (EKS, t3.small) — under-provisioned for load
- PostgreSQL 15 (RDS, db.t3.small, Multi-AZ disabled)
- AWS SQS FIFO queue for Stripe webhook processing
- Stripe SDK v7 with synchronous tax calculation (3rd-party API)
- Dead-letter queue configured but not alarmed
Known architecture gaps:
- Only 2 replicas — pod failure = 50% capacity loss immediately
- Synchronous Stripe+tax API calls block goroutines (no timeout <5s)
- DB connection pool: max=10 (too low for burst traffic)
- PDB (PodDisruptionBudget) not set → rolling update can kill both pods
- No goroutine dumps on high-latency; no pprof endpoint exposed
""",
}

SIMULATED_LOGS = {
    "auth_service": [
        "ERROR 2024-06-27 02:14:33 auth.jwt: jose.ErrSignatureInvalid: signature verification failed (key_id=abc123)",
        "WARN  2024-06-27 02:14:34 auth.cache: Redis GET miss for token_hash=f7a3...; falling back to DB verify",
        "ERROR 2024-06-27 02:14:35 auth.db: pq: sorry, too many clients already (pool exhausted)",
        "ERROR 2024-06-27 02:14:36 auth.server: 5xx storm — 1243 requests in 1s returning 503",
    ],
    "data_pipeline": [
        "ERROR 2024-10-23 07:12:01 schema.registry: disk usage 100% — all producer writes rejected",
        "ERROR 2024-10-23 07:12:05 kafka.producer: SCHEMA_REGISTRY_UNAVAILABLE for topic=user-events",
        "WARN  2024-10-23 07:11:50 kafka.consumer: consumer group rebalance — 847 partitions reassigned",
    ],
    "billing_api": [
        "ERROR 2025-02-27 16:33:11 billing.tax: context deadline exceeded (3rd-party tax API >5s)",
        "ERROR 2025-02-27 16:33:12 billing.stripe: goroutine blocked waiting for tax calculation",
        "WARN  2025-02-27 16:33:00 billing.db: slow query 8.2s on invoices table (seq scan, missing index)",
    ],
    "api_gateway": [
        "WARN  2025-01-12 13:47:22 kong.waf: rule 942100 blocked 1847 requests in 60s (false positive)",
        "ERROR 2025-01-12 13:47:25 kong.redis: dial tcp: connection refused (pool exhausted)",
    ],
}


class ClaudeAdapter(IAIAnalyzer):

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.enabled = bool(self.api_key)

    def _build_prompt(
        self,
        service_name: str,
        sli_type: str,
        service: ServiceMetrics,
        incidents: list[Incident],
    ) -> str:
        recent_incidents = [
            f"- [{i.severity.upper()}] {i.started_at[:16]} | {i.title} ({i.duration_minutes}m) | {i.root_cause}"
            for i in incidents[:5]
        ]
        arch = SIMULATED_ARCH.get(service_name, "Architecture context not available.")
        logs = "\n".join(SIMULATED_LOGS.get(service_name, ["No recent log samples available."]))

        return f"""You are a senior Site Reliability Engineer performing a root-cause and remediation analysis for a reliability breach in production.

## SERVICE CONTEXT
Service: {service_name} ({service.display_name})
Description: {service.description}
Tech Stack: {", ".join(service.tech_stack)}
Tier: {service.tier}

## CURRENT SLI BREACH
SLI Type: {sli_type}
Current Availability: {service.avg_availability_pct}%
SLO Target: {service.slos[0].target if service.slos else "N/A"}%
Error Rate: {service.avg_error_rate_pct}%
Latency p99: {service.avg_latency_p99_ms}ms
Error Budget Remaining: {service.error_budget.remaining_pct}%
Error Budget Burn Rate: {service.error_budget.burn_rate_current}x

## ARCHITECTURE & INFRASTRUCTURE (from Terraform)
{arch}

## RECENT INCIDENT HISTORY
{chr(10).join(recent_incidents) if recent_incidents else "No recent incidents found."}

## RECENT LOG SAMPLES
{logs}

## ANALYSIS INSTRUCTIONS
Provide a structured JSON analysis. Be specific — do NOT give generic "scale up" advice. Instead:
1. Identify the most likely root causes based on the architecture gaps and log evidence.
2. For each action item, reference the specific Terraform resource or code component to change.
3. Explicitly identify what observability data is MISSING that would improve accuracy (thread dumps, traces, heap dumps, profiling data).
4. For each missing data type, provide an automated collection trigger (e.g., Kubernetes pre-hook, alarm-triggered Lambda, async profiler at X% CPU).
5. Cost-aware: prefer fixes that don't require instance class upgrades if config changes suffice.

Respond ONLY with this exact JSON (no markdown, no preamble):
{{
  "summary": "2-3 sentence plain-English summary of the breach",
  "confidence": "high|medium|low",
  "root_cause_hypotheses": [
    {{"rank": 1, "hypothesis": "...", "evidence": "...", "confidence": "high|medium|low"}},
    {{"rank": 2, "hypothesis": "...", "evidence": "...", "confidence": "high|medium|low"}}
  ],
  "action_items": {{
    "immediate": [{{"action": "...", "component": "...", "rationale": "..."}}],
    "short_term": [{{"action": "...", "component": "...", "rationale": "..."}}],
    "long_term":  [{{"action": "...", "component": "...", "rationale": "..."}}]
  }},
  "observability_gaps": [
    {{"gap": "...", "impact": "...", "how_to_close": "...", "automation_trigger": "..."}}
  ],
  "automated_remediation": [
    {{"trigger_condition": "...", "action": "...", "implementation_sketch": "..."}}
  ],
  "caveats": ["..."],
  "data_needed_to_improve_analysis": ["..."]
}}"""

    def analyse(
        self,
        service_name: str,
        sli_type: str,
        service_metrics: ServiceMetrics,
        incidents: list[Incident],
    ) -> AnalysisResult:
        now = datetime.now(timezone.utc).isoformat()

        if not self.enabled:
            return self._stub_result(service_name, sli_type, now)

        prompt = self._build_prompt(service_name, sli_type, service_metrics, incidents)

        try:
            resp = httpx.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"].strip()
            data = json.loads(text)

            return AnalysisResult(
                service_name=service_name,
                sli_type=sli_type,
                summary=data.get("summary", ""),
                confidence=data.get("confidence", "medium"),
                root_cause_hypotheses=data.get("root_cause_hypotheses", []),
                action_items=data.get("action_items", {}),
                observability_gaps=data.get("observability_gaps", []),
                automated_remediation=data.get("automated_remediation", []),
                caveats=data.get("caveats", []),
                data_needed=data.get("data_needed_to_improve_analysis", []),
                ai_model=MODEL,
                generated_at=now,
            )
        except Exception as exc:
            return AnalysisResult(
                service_name=service_name,
                sli_type=sli_type,
                summary=f"Analysis failed: {exc}. Check ANTHROPIC_API_KEY and network connectivity.",
                confidence="low",
                root_cause_hypotheses=[],
                action_items={},
                observability_gaps=[],
                automated_remediation=[],
                caveats=["API call failed — ensure ANTHROPIC_API_KEY is set in .env"],
                data_needed=[],
                ai_model=MODEL,
                generated_at=now,
            )

    def _stub_result(self, service_name: str, sli_type: str, now: str) -> AnalysisResult:
        """Returned when no API key is configured — shows structure without AI call."""
        return AnalysisResult(
            service_name=service_name,
            sli_type=sli_type,
            summary=(
                f"[DEMO MODE — no ANTHROPIC_API_KEY set] "
                f"This is a stub analysis for {service_name} / {sli_type}. "
                "Add ANTHROPIC_API_KEY to .env to enable real AI-powered analysis."
            ),
            confidence="low",
            root_cause_hypotheses=[
                {
                    "rank": 1,
                    "hypothesis": "Single-AZ deployment with no connection pooling causes cascading failures under load",
                    "evidence": "Architecture shows t3.small pods without PgBouncer and Multi-AZ disabled",
                    "confidence": "high",
                },
                {
                    "rank": 2,
                    "hypothesis": "Missing distributed tracing prevents identifying the slowest call in the chain",
                    "evidence": "No OpenTelemetry instrumentation visible in tech stack",
                    "confidence": "medium",
                },
            ],
            action_items={
                "immediate": [
                    {"action": "Increase DB connection pool size", "component": "rds_parameter_group", "rationale": "Current max=10 is exhausted under burst traffic"},
                ],
                "short_term": [
                    {"action": "Deploy PgBouncer sidecar", "component": "k8s/deployment.yaml", "rationale": "Reduces DB connections from O(pods×threads) to a fixed pool"},
                    {"action": "Enable Multi-AZ on RDS", "component": "terraform/rds.tf", "rationale": "Single AZ is a reliability single point of failure"},
                ],
                "long_term": [
                    {"action": "Instrument with OpenTelemetry", "component": "application code", "rationale": "Without traces, root cause analysis relies on guesswork"},
                ],
            },
            observability_gaps=[
                {
                    "gap": "Thread dumps not collected during incidents",
                    "impact": "Cannot identify thread contention or deadlocks post-incident",
                    "how_to_close": "Attach async-profiler as init container; configure jstack on SIGTERM",
                    "automation_trigger": "Kubernetes liveness probe failure → pre-stop hook runs jstack",
                },
                {
                    "gap": "No distributed traces (OpenTelemetry not instrumented)",
                    "impact": "Cannot see which downstream call contributes to latency spikes",
                    "how_to_close": "Add opentelemetry-sdk; export to Jaeger or AWS X-Ray",
                    "automation_trigger": "Deploy as part of next sprint; zero-downtime instrumentation",
                },
            ],
            automated_remediation=[
                {
                    "trigger_condition": "error_rate > 1% for 5 consecutive minutes",
                    "action": "Scale replicas from 3 to 6, capture thread dump",
                    "implementation_sketch": "KEDA ScaledObject + Kubernetes Job for jstack capture",
                },
            ],
            caveats=["DEMO MODE: Set ANTHROPIC_API_KEY in .env for real analysis"],
            data_needed=["Thread dumps at time of incident", "Distributed traces", "GC pause metrics"],
            ai_model=MODEL,
            generated_at=now,
        )
