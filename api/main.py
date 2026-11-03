"""Teduh FastAPI Application Entry Point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import get_pool, close_pool
from api.routes.navigation import router as navigation_router
from api.routes.dashboard import router as dashboard_router
from api.routes.cctv import router as cctv_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage connection pool lifecycle."""
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Teduh API",
    description="Thermal-comfort-based pedestrian navigation for Surabaya Smart City",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access.
# CORS_ORIGINS: comma-separated list of allowed origins (default "*" for local dev).
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(navigation_router, prefix="/api", tags=["Navigation"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(cctv_router, prefix="/api", tags=["CCTV"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "teduh-api"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Teduh API",
        "version": "0.2.0",
        "docs": "/docs",
        "description": "Thermal comfort pedestrian navigation - Surabaya",
    }
