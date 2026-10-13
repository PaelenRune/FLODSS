"""Primary API router aggregating all route controllers with controlled access dependencies."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes import (
    health,
    auth,
    projects,
    problems,
    layouts,
    evaluation,
    algorithms,
    benchmarks,
    pareto,
    strategy,
    ai,
)

api_router = APIRouter()

# Unauthenticated / Self-authenticated endpoints
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Project & Experiment management (enforces granular IDOR/role access within route handlers)
api_router.include_router(projects.router)
api_router.include_router(projects.experiment_router)

# Research computation endpoints (require active authenticated user session)
api_router.include_router(problems.router, dependencies=[Depends(get_current_user)])
api_router.include_router(layouts.router, dependencies=[Depends(get_current_user)])
api_router.include_router(evaluation.router, dependencies=[Depends(get_current_user)])
api_router.include_router(algorithms.router, dependencies=[Depends(get_current_user)])
api_router.include_router(benchmarks.router, dependencies=[Depends(get_current_user)])
api_router.include_router(pareto.router, dependencies=[Depends(get_current_user)])
api_router.include_router(strategy.router, dependencies=[Depends(get_current_user)])
api_router.include_router(ai.router, dependencies=[Depends(get_current_user)])
