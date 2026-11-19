"""Background job (APScheduler) that runs the SLA check every few minutes."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.services.sla_service import check_sla_and_escalate

logger = logging.getLogger("campusfix.sla_job")

SLA_JOB_ID = "sla_escalation_job"


def run_sla_escalation_job() -> None:
    """Run one SLA check. Errors are logged so one failure does not stop future runs."""
    try:
        summary = check_sla_and_escalate()
        logger.info("SLA check finished: %s", summary)
    except Exception:
        logger.exception("SLA check failed")


def create_sla_scheduler() -> BackgroundScheduler:
    """Create a scheduler that runs the SLA job every SLA_CHECK_INTERVAL_MINUTES (default 15)."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_sla_escalation_job,
        trigger="interval",
        minutes=settings.sla_check_interval_minutes,
        id=SLA_JOB_ID,
        replace_existing=True,
    )
    return scheduler
