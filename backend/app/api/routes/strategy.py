"""API endpoints for Adaptive Strategy Engine v1: problem analysis and autonomous solving."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_job_slot

from app.models.problem import FacilityLayoutProblem
from app.optimization.adaptive import (
    AdaptiveConfig,
    AdaptiveStrategyResult,
    RuleBasedStrategySelector,
    StrategyExecutionEngine,
    StrategyPipeline,
)
from app.services.problem_analyzer import ProblemAnalyzer, ProblemFingerprint
from app.services.problem_service import problem_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategy", tags=["strategy"])

DATA_EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "data" / "examples"


def _resolve_problem(
    problem_id: Optional[str] = None,
    problem_payload: Optional[FacilityLayoutProblem] = None,
) -> FacilityLayoutProblem:
    """Resolve problem instance from explicit payload or registered example files."""
    if problem_payload is not None:
        return problem_payload

    if not problem_id:
        problem_id = "FLP_INDUSTRIAL_10"

    id_to_file = {
        "FLP_ACADEMIC_4": "sample_academic_4.json",
        "FLP_MEDIUM_6": "sample_medium_plant.json",
        "FLP_INDUSTRIAL_10": "sample_plant.json",
        "FLP_EXPANSION_8": "sample_expansion_8.json",
        "FLP_LOGISTICS_5": "sample_logistics_5.json",
        "HIGH_DENSITY_15": "synthetic_high_density_15.json",
        "HIGH_DENSITY_20": "synthetic_high_density_20.json",
        "CONSTRAINED_FACTORY_12": "synthetic_constrained_factory_12.json",
        "LOGISTICS_FACTORY_15": "synthetic_logistics_factory_15.json",
    }

    if problem_id in id_to_file:
        file_path = DATA_EXAMPLES_DIR / id_to_file[problem_id]
        if file_path.exists():
            return problem_service.load_problem(file_path)

    # Fallback to general problem loader
    try:
        return problem_service.load_problem(problem_id)
    except Exception as ex:
        raise HTTPException(
            status_code=404,
            detail=f"Problem '{problem_id}' could not be resolved: {str(ex)}",
        )


class StrategyAnalyzeRequest(BaseModel):
    """Payload for analyzing problem fingerprint and recommending strategy."""

    problem_id: Optional[str] = Field(default=None, description="ID of problem to analyze")
    problem: Optional[FacilityLayoutProblem] = Field(default=None, description="Optional explicit problem definition")
    has_initial_layout: bool = Field(default=False, description="True if an initial layout is available")


class StrategyAnalyzeResponse(BaseModel):
    """Response containing structural fingerprint and recommended strategy pipeline."""

    problem_id: str
    fingerprint: ProblemFingerprint
    selected_strategy: StrategyPipeline


class StrategySolveRequest(BaseModel):
    """Payload for executing adaptive strategy solver."""

    problem_id: Optional[str] = Field(default=None, description="ID of problem to solve")
    problem: Optional[FacilityLayoutProblem] = Field(default=None, description="Optional explicit problem definition")
    config: Optional[AdaptiveConfig] = Field(default=None, description="Adaptive execution and budget settings")
    initial_layout: Optional[Dict[str, Any]] = Field(default=None, description="Optional baseline layout dictionary")


@router.post("/analyze", response_model=StrategyAnalyzeResponse, summary="Analyze Problem and Recommend Strategy")
def analyze_strategy(payload: StrategyAnalyzeRequest):
    """Compute characteristic problem fingerprint and evaluate rule-based strategy recommendation."""
    target_problem = _resolve_problem(payload.problem_id, payload.problem)
    fingerprint = ProblemAnalyzer.extract_fingerprint(target_problem)
    strategy = RuleBasedStrategySelector.select_strategy(
        fingerprint,
        has_initial_layout=payload.has_initial_layout,
    )

    return StrategyAnalyzeResponse(
        problem_id=target_problem.id,
        fingerprint=fingerprint,
        selected_strategy=strategy,
    )


@router.post("/solve", response_model=AdaptiveStrategyResult, summary="Execute Adaptive Strategy Solver")
def solve_strategy(
    payload: StrategySolveRequest,
    _slot: Any = Depends(get_job_slot),
):
    """Execute adaptive strategy pipeline with resource budgeting, validation, fallback, and Pareto analysis."""
    target_problem = _resolve_problem(payload.problem_id, payload.problem)
    config = payload.config or AdaptiveConfig()

    try:
        result = StrategyExecutionEngine.execute(
            problem=target_problem,
            config=config,
            initial_layout=payload.initial_layout,
        )
        return result
    except Exception as ex:
        logger.exception("Adaptive strategy execution failed: %s", ex)
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive strategy execution failed: {str(ex)}",
        )
