"""
Sentinel — FastAPI application entry point.
Wires up hexagonal architecture: ports ← adapters → application services.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .adapters.metrics.prometheus_adapter import PrometheusAdapter
from .adapters.ai.claude_adapter import ClaudeAdapter
from .application.services import SLOService, AnalysisService
from .api.routes import make_router

app = FastAPI(
    title="Sentinel — Reliability Conformance API",
    description="SLI/SLO/SLA tracking with AI-powered breach analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency wiring (hexagonal) ─────────────────────────────────────────────
repo     = PrometheusAdapter()          # swap to real PrometheusAdapter(url=...) here
ai       = ClaudeAdapter()
slo_svc  = SLOService(repo)
ai_svc   = AnalysisService(repo, ai)

app.include_router(make_router(slo_svc, ai_svc))

@app.get("/")
def root():
    return {
        "name": "Sentinel",
        "tagline": "Reliability Conformance Dashboard",
        "docs": "/docs",
        "api": "/api/v1/dashboard",
        "ai_enabled": ai.enabled,
    }
