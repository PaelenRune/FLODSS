"""API endpoints for layout evaluation, multi-metric scoring, and comparative ranking."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution
from app.services.problem_service import problem_service
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine, EvaluationReport, ComparisonReport
from app.evaluation.metrics import MetricType, MetricDirection


router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluateLayoutRequest(BaseModel):
    """Payload to evaluate a single layout against a problem definition."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded example problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    layout: Dict[str, Any] = Field(..., description="Continuous layout or solution payload to evaluate")
    config: Optional[EvaluationConfig] = Field(None, description="Optional evaluation configuration overrides")
    metrics: Optional[List[str]] = Field(None, description="Optional list of specific metric names to compute")


class CompareLayoutsRequest(BaseModel):
    """Payload to evaluate and rank multiple candidate layouts."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded example problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    layouts: List[Dict[str, Any]] = Field(..., min_length=1, description="List of layout payloads to compare")
    config: Optional[EvaluationConfig] = Field(None, description="Optional evaluation configuration overrides")


def _resolve_problem(
    problem_id: Optional[str], problem_data: Optional[Dict[str, Any]]
) -> FacilityLayoutProblem:
    """Resolve problem from either an inline payload or preloaded storage."""
    if problem_data:
        try:
            return FacilityLayoutProblem.model_validate(problem_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid problem payload: {str(e)}",
            )
    if problem_id:
        try:
            return problem_service.get_example_by_id(problem_id)
        except (KeyError, FileNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem with ID '{problem_id}' not found.",
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either 'problem' or 'problem_id' must be provided.",
    )


@router.get("/metrics", response_model=Dict[str, Any])
def list_available_metrics() -> Dict[str, Any]:
    """Retrieve all available evaluation metrics with standard units and optimization directions."""
    engine = EvaluationEngine()
    metrics_info = []
    for name in engine.registered_metrics:
        evaluator = engine._evaluators[name]
        metrics_info.append({
            "name": name,
            "display_name": evaluator.display_name,
            "unit": evaluator.unit,
            "direction": evaluator.direction.value,
        })
    return {
        "status": "success",
        "count": len(metrics_info),
        "metrics": metrics_info,
    }


@router.post("/evaluate", response_model=EvaluationReport)
def evaluate_layout(request: EvaluateLayoutRequest) -> EvaluationReport:
    """Evaluate a single candidate layout against facility problem requirements."""
    problem = _resolve_problem(request.problem_id, request.problem)
    engine = EvaluationEngine(config=request.config)
    try:
        report = engine.evaluate(
            problem=problem,
            solution=request.layout,
            config=request.config,
            metrics_subset=request.metrics,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.post("/compare", response_model=ComparisonReport)
def compare_layouts(request: CompareLayoutsRequest) -> ComparisonReport:
    """Evaluate and rank multiple alternative layouts using multi-objective normalization."""
    problem = _resolve_problem(request.problem_id, request.problem)
    engine = EvaluationEngine(config=request.config)
    try:
        comparison = engine.evaluate_many(
            problem=problem,
            solutions=request.layouts,
            config=request.config,
        )
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Layout comparison failed: {str(e)}",
        )
