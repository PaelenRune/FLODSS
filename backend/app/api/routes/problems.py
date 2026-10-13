"""API endpoints for facility layout problem management and validation."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.models.problem import FacilityLayoutProblem
from app.services.problem_service import (
    ProblemSummary,
    ProblemValidationReport,
    problem_service,
)

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("/examples", response_model=List[ProblemSummary], summary="List Example Problems")
def list_examples() -> List[ProblemSummary]:
    """Retrieve catalog of available benchmark problems stored in the filesystem."""
    return problem_service.list_example_problems()


@router.get("/examples/{problem_id}", response_model=FacilityLayoutProblem, summary="Get Example Problem by ID")
def get_example(problem_id: str) -> FacilityLayoutProblem:
    """Load and return the complete specification of a benchmark problem."""
    try:
        return problem_service.get_example_problem(problem_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Example problem '{problem_id}' was not found.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load example problem: {str(e)}",
        )


@router.post("/validate", response_model=ProblemValidationReport, summary="Validate Problem Payload")
def validate_problem_payload(payload: Dict[str, Any]) -> ProblemValidationReport:
    """Validate a candidate layout problem JSON schema and structural integrity.
    
    Checks for:
    - Department consistency & unique IDs
    - Facility boundary feasibility & area utilization
    - Relational integrity of flows, closeness ratings, and constraints
    - Objective weights and parameters
    
    Returns validation outcome, error diagnostics, and problem fingerprint.
    """
    return problem_service.validate_problem(payload)
