"""
Ports (interfaces) — hexagonal architecture.
The application core depends only on these abstractions.
"""
from abc import ABC, abstractmethod
from .models import DashboardSummary, ServiceMetrics, SLATier, Incident, AnalysisResult


class IMetricsRepository(ABC):
    """Port for reading SLI/SLO metric data. Swap mock → real Prometheus here."""

    @abstractmethod
    def get_dashboard(self, window_days: int = 30) -> DashboardSummary:
        ...

    @abstractmethod
    def get_service(self, name: str, window_days: int = 30) -> ServiceMetrics:
        ...

    @abstractmethod
    def get_sla_tiers(self) -> list[SLATier]:
        ...

    @abstractmethod
    def get_incidents(self, service: str | None = None, limit: int = 50) -> list[Incident]:
        ...

    @abstractmethod
    def get_availability_series(self, service: str, days: int = 30) -> list[dict]:
        ...

    @abstractmethod
    def get_error_budget_series(self, service: str, days: int = 30) -> list[dict]:
        ...

    @abstractmethod
    def get_heatmap(self, service: str, days: int = 90) -> list[dict]:
        ...


class IAIAnalyzer(ABC):
    """Port for AI-powered breach analysis."""

    @abstractmethod
    def analyse(
        self,
        service_name: str,
        sli_type: str,
        service_metrics: ServiceMetrics,
        incidents: list[Incident],
    ) -> AnalysisResult:
        ...
