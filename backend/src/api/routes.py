"""FastAPI route definitions — thin HTTP adapter layer."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..application.services import SLOService, AnalysisService

router = APIRouter(prefix="/api/v1")


class AnalyseRequest(BaseModel):
    service_name: str
    sli_type: str = "availability"


def make_router(slo: SLOService, analysis: AnalysisService) -> APIRouter:

    @router.get("/dashboard")
    def dashboard(window: int = Query(30, ge=7, le=365)):
        return slo.dashboard(window)

    @router.get("/services/{name}")
    def service(name: str, window: int = Query(30, ge=7, le=365)):
        try:
            return slo.service(name, window)
        except KeyError:
            raise HTTPException(404, f"Service '{name}' not found")

    @router.get("/services/{name}/availability")
    def availability(name: str, days: int = Query(30, ge=1, le=365)):
        try:
            return slo.availability_series(name, days)
        except KeyError:
            raise HTTPException(404, f"Service '{name}' not found")

    @router.get("/services/{name}/budget")
    def budget(name: str, days: int = Query(30, ge=1, le=365)):
        try:
            return slo.error_budget_series(name, days)
        except KeyError:
            raise HTTPException(404, f"Service '{name}' not found")

    @router.get("/services/{name}/heatmap")
    def heatmap(name: str, days: int = Query(90, ge=7, le=365)):
        try:
            return slo.heatmap(name, days)
        except KeyError:
            raise HTTPException(404, f"Service '{name}' not found")

    @router.get("/sla")
    def sla():
        return slo.sla_tiers()

    @router.get("/incidents")
    def incidents(service: str | None = None, limit: int = Query(50, ge=1, le=200)):
        return slo.incidents(service, limit)

    @router.post("/analyse")
    def analyse(req: AnalyseRequest):
        return analysis.analyse(req.service_name, req.sli_type)

    @router.get("/health")
    def health():
        return {"status": "ok", "service": "sentinel-backend"}

    return router
