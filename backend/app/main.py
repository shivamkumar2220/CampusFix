"""Entry point: creates the FastAPI app, adds CORS, includes routers and starts the SLA scheduler.

Start the server from the backend folder with:
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.jobs.sla_escalation_job import create_sla_scheduler
from app.routes import (
    auth_routes,
    complaint_routes,
    dashboard_routes,
    notification_routes,
    user_routes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Start the background SLA scheduler when the server starts, stop it when it shuts down."""
    scheduler = create_sla_scheduler() if settings.enable_scheduler else None
    if scheduler:
        scheduler.start()
        logging.getLogger("campusfix").info(
            "SLA scheduler started (every %s minutes)", settings.sla_check_interval_minutes
        )
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="CampusFix API",
    description="Campus IT & Facility Issue Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS lets the HTML pages (opened from another address or from file://) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=False,  # we send the JWT in a header, not in cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(complaint_routes.router)
app.include_router(user_routes.router)
app.include_router(notification_routes.router)
app.include_router(dashboard_routes.router)


@app.get("/", tags=["Health"])
def health_check() -> dict:
    """Check that the API is running."""
    return {
        "message": "CampusFix API is running.",
        "login_page": "/app/pages/login.html",
        "api_docs": "/docs",
    }


# Serve the HTML/CSS/JS frontend from the same server, so only ONE program has to run.
# The login page is then at http://localhost:8000/app/pages/login.html
FRONTEND_FOLDER = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_FOLDER.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTEND_FOLDER, html=True), name="frontend")
