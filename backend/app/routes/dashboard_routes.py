"""Admin dashboard routes: statistics and a manual SLA check button."""

from fastapi import APIRouter, Depends

from app.schemas.dashboard_schemas import DashboardStatsResponse, SlaCheckResponse
from app.security.role_checker import require_roles
from app.services import dashboard_service, sla_service

router = APIRouter(prefix="/api/dashboard", tags=["Admin Dashboard"])

admin_only = require_roles("admin")


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(current_user: dict = Depends(admin_only)) -> dict:
    """Admin: numbers for the dashboard cards and charts."""
    return dashboard_service.get_dashboard_stats()


@router.post("/run-sla-check", response_model=SlaCheckResponse)
def run_sla_check_now(current_user: dict = Depends(admin_only)) -> dict:
    """Admin: run the SLA escalation check immediately (normally it runs every 15 minutes)."""
    return sla_service.check_sla_and_escalate()
