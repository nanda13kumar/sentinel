"""
Application services — orchestration layer.
Depends only on ports (interfaces), not concrete adapters.
"""
from dataclasses import asdict
from ..domain.ports import IMetricsRepository, IAIAnalyzer
from ..domain.models import DashboardSummary, ServiceMetrics, AnalysisResult


def _to_dict(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


class SLOService:
    def __init__(self, repo: IMetricsRepository):
        self._repo = repo

    def dashboard(self, window_days: int = 30) -> dict:
        return _to_dict(self._repo.get_dashboard(window_days))

    def service(self, name: str, window_days: int = 30) -> dict:
        return _to_dict(self._repo.get_service(name, window_days))

    def sla_tiers(self) -> list:
        return [_to_dict(t) for t in self._repo.get_sla_tiers()]

    def incidents(self, service: str | None = None, limit: int = 50) -> list:
        return [_to_dict(i) for i in self._repo.get_incidents(service, limit)]

    def availability_series(self, service: str, days: int = 30) -> list:
        return self._repo.get_availability_series(service, days)

    def error_budget_series(self, service: str, days: int = 30) -> list:
        return self._repo.get_error_budget_series(service, days)

    def heatmap(self, service: str, days: int = 90) -> list:
        return self._repo.get_heatmap(service, days)


class AnalysisService:
    def __init__(self, repo: IMetricsRepository, ai: IAIAnalyzer):
        self._repo = repo
        self._ai   = ai

    def analyse(self, service_name: str, sli_type: str) -> dict:
        svc = self._repo.get_service(service_name, window_days=30)
        incs = self._repo.get_incidents(service_name, limit=10)
        result = self._ai.analyse(service_name, sli_type, svc, incs)
        return _to_dict(result)
