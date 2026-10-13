"""API routes for Pareto Frontier analysis, multi-objective ranking, and decision support."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.evaluation.config import EvaluationConfig
from app.models.problem import FacilityLayoutProblem
from app.optimization.pareto import (
    ObjectiveDefinition,
    ParetoAnalysisResult,
    ParetoCandidate,
    ParetoFrontierService,
    TradeOffComparison,
    get_default_pareto_objectives,
)
from app.services.problem_service import problem_service


router = APIRouter(prefix="/pareto", tags=["pareto"])

DATA_EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "data" / "examples"


class ParetoAnalyzeRequest(BaseModel):
    """Payload for Pareto Frontier multi-objective analysis."""

    problem_id: str = Field(default="FLP_INDUSTRIAL_10", description="ID of problem to analyze")
    candidates: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional explicit candidate layout payloads to include in portfolio",
    )
    include_saved_baselines: bool = Field(
        default=True,
        description="Include saved manual, guillotine, and GA benchmark baselines if available",
    )
    objectives: Optional[List[ObjectiveDefinition]] = Field(
        default=None,
        description="Optional custom objective definitions (defaults to MHC, Rel Satisfaction, Soft Penalty)",
    )
    priority_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional custom decision weights for multi-criteria utility recommendation",
    )


class ParetoCompareRequest(BaseModel):
    """Payload for pairwise trade-off comparison."""

    candidate_a: ParetoCandidate
    candidate_b: ParetoCandidate
    objectives: Optional[List[ObjectiveDefinition]] = None


@router.get("/objectives", response_model=List[ObjectiveDefinition], summary="List Default Pareto Objectives")
def get_objectives():
    """Retrieve the standard 3-objective configuration for Pareto analysis."""
    return get_default_pareto_objectives()


@router.post("/analyze", response_model=ParetoAnalysisResult, summary="Execute Pareto Frontier Analysis")
def analyze_pareto(payload: ParetoAnalyzeRequest):
    """Analyze a candidate layout portfolio, filter invalid designs, assign Pareto ranks, and generate recommendations."""
    # 1. Resolve problem
    try:
        problem = problem_service.get_example_problem(payload.problem_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Problem '{payload.problem_id}' not found in registered problems",
        )

    portfolio: List[Any] = []

    # 2. Add saved baselines if requested
    if payload.include_saved_baselines:
        saved_files = [
            ("Manual Baseline", "sample_layout.json"),
            ("Guillotine Baseline", "generated_industrial_10.json"),
            ("GA Best Solution (Seed 2024)", "ga_optimized_industrial_10.json"),
        ]

        for label, fname in saved_files:
            fpath = DATA_EXAMPLES_DIR / fname
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    if d.get("problem_id") == problem.id:
                        d["id"] = label
                        d["algorithm_name"] = label
                        portfolio.append(d)
                except Exception:
                    pass

        # Also load additional multi-seed GA runs if available
        seeds_path = DATA_EXAMPLES_DIR / "pareto_additional_seeds.json"
        if seeds_path.exists():
            try:
                with open(seeds_path, "r", encoding="utf-8") as f:
                    seeds_data = json.load(f)
                for item in seeds_data:
                    if item.get("problem_id") == problem.id:
                        portfolio.append(item)
            except Exception:
                pass

    # 3. Add caller-provided candidate layouts
    if payload.candidates:
        portfolio.extend(payload.candidates)

    if not portfolio:
        raise HTTPException(
            status_code=400,
            detail=f"No candidate layouts found or provided for problem '{payload.problem_id}'",
        )

    # 4. Execute Pareto Analysis
    try:
        result = ParetoFrontierService.analyze(
            problem=problem,
            raw_candidates=portfolio,
            objectives=payload.objectives,
            config=EvaluationConfig(),
            custom_weights=payload.priority_weights,
        )
        return result
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Pareto analysis failed: {str(ex)}",
        )


@router.post("/compare", response_model=TradeOffComparison, summary="Compare Two Pareto Candidates")
def compare_candidates(payload: ParetoCompareRequest):
    """Compute explicit pairwise trade-off analysis between two candidates."""
    eff_objectives = payload.objectives or get_default_pareto_objectives()
    return ParetoFrontierService.compare_pair(
        payload.candidate_a,
        payload.candidate_b,
        eff_objectives,
    )
