"""API endpoints for algorithm discovery, execution, and trace reporting."""

from pathlib import Path
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_job_slot

from app.algorithms.registry import AlgorithmRegistry
from app.algorithms.corelap.config import CORELAPConfig
from app.algorithms.corelap.trace import CORELAPExecutionTrace
from app.algorithms.corelap.solver import CORELAPAlgorithm
from app.algorithms.craft.config import CRAFTConfig
from app.algorithms.craft.models import CRAFTSolverResult, CRAFTExecutionTrace
from app.algorithms.craft.solver import CRAFTAlgorithm, _normalize_initial_layout
from app.algorithms.aldep.config import ALDEPConfig
from app.algorithms.aldep.models import (
    ALDEPSolverResult,
    ALDEPExecutionTrace,
    ALDEPCandidateResult,
)
from app.algorithms.aldep.solver import ALDEPAlgorithm
from app.algorithms.generator.models import GeneratorConfig, GeneratorResult
from app.algorithms.generator.solver import FeasibleLayoutGenerator
from app.algorithms.ga.models import GAConfig, GAResult
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, GridLayout
from app.models.solution import LayoutSolution
from app.services.problem_service import problem_service
from app.services.layout_validator import LayoutValidator, LayoutValidationResult
from app.evaluation.engine import EvaluationEngine, EvaluationReport
from app.evaluation.config import EvaluationConfig


router = APIRouter(prefix="/algorithms", tags=["algorithms"])

DATA_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "examples"


class CORELAPSolveRequest(BaseModel):
    """Payload to trigger CORELAP layout construction."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    config: Optional[CORELAPConfig] = Field(None, description="CORELAP configuration options")


class CORELAPSolveResponse(BaseModel):
    """Standardized response from CORELAP solver."""
    solution: LayoutSolution = Field(..., description="Generated standardized layout solution")
    continuous_layout: ContinuousLayout = Field(..., description="Continuous geometric representation")
    trace: CORELAPExecutionTrace = Field(..., description="Step-by-step explainability trace")
    validation: LayoutValidationResult = Field(..., description="Geometric feasibility validation")
    evaluation: EvaluationReport = Field(..., description="Evaluation report from EvaluationEngine")


class CRAFTSolveRequest(BaseModel):
    """Payload to trigger CRAFT layout improvement."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    initial_layout_id: Optional[str] = Field(None, description="Identifier of preloaded initial layout")
    initial_layout: Optional[Dict[str, Any]] = Field(None, description="Inline initial layout payload")
    config: Optional[CRAFTConfig] = Field(None, description="CRAFT algorithm configuration options")
    evaluation_config: Optional[EvaluationConfig] = Field(None, description="Standardized evaluation engine configuration")


class CRAFTSolveResponse(BaseModel):
    """Standardized response from CRAFT improvement solver."""
    solution: LayoutSolution = Field(..., description="Improved standardized layout solution")
    continuous_layout: ContinuousLayout = Field(..., description="Final optimized continuous layout")
    initial_layout: ContinuousLayout = Field(..., description="Starting baseline continuous layout")
    result: CRAFTSolverResult = Field(..., description="Detailed CRAFT solver result and trace")
    initial_evaluation: EvaluationReport = Field(..., description="Baseline evaluation report")
    final_evaluation: EvaluationReport = Field(..., description="Optimized evaluation report")
    trace: CRAFTExecutionTrace = Field(..., description="Step-by-step optimization trace")


class ALDEPSolveRequest(BaseModel):
    """Payload to trigger ALDEP layout construction."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    config: Optional[ALDEPConfig] = Field(None, description="ALDEP algorithm configuration options")


class ALDEPSolveResponse(BaseModel):
    """Standardized response from ALDEP solver."""
    solution: LayoutSolution = Field(..., description="Top-ranked standardized layout solution")
    continuous_layout: ContinuousLayout = Field(..., description="Best candidate continuous layout")
    grid_layout: Optional[GridLayout] = Field(None, description="Native discrete grid layout representation")
    best_candidate: ALDEPCandidateResult = Field(..., description="Top-ranked candidate detail")
    candidates: List[ALDEPCandidateResult] = Field(default_factory=list, description="All generated candidate alternatives")
    result: ALDEPSolverResult = Field(..., description="Detailed ALDEP solver result")
    trace: ALDEPExecutionTrace = Field(..., description="Step-by-step optimization trace")
    validation: LayoutValidationResult = Field(..., description="Geometric validation of best candidate")
    evaluation: EvaluationReport = Field(..., description="Evaluation report of best candidate")


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
            return problem_service.get_example_problem(problem_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem with ID '{problem_id}' not found.",
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either 'problem' or 'problem_id' must be provided.",
    )


def _resolve_initial_layout(
    layout_id: Optional[str], layout_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Resolve initial layout from either an inline payload or preloaded storage."""
    if layout_data:
        return layout_data

    if layout_id:
        if DATA_EXAMPLES_DIR.exists():
            for file_path in DATA_EXAMPLES_DIR.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("id") == layout_id or file_path.stem == layout_id:
                            return data
                except Exception:
                    continue
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Initial layout with ID '{layout_id}' not found.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either 'initial_layout' or 'initial_layout_id' must be provided.",
    )


@router.get("", response_model=List[Dict[str, Any]], summary="List all registered layout algorithms")
def list_algorithms() -> List[Dict[str, Any]]:
    """Retrieve metadata and parameter specs for all registered optimization algorithms."""
    return AlgorithmRegistry.list_available()


@router.post(
    "/corelap/solve",
    response_model=CORELAPSolveResponse,
    summary="Construct layout using CORELAP heuristic",
)
def solve_corelap(
    payload: CORELAPSolveRequest,
    _slot: Any = Depends(get_job_slot),
) -> CORELAPSolveResponse:
    """Run deterministic CORELAP v1.0 layout construction.
    
    Returns the generated layout, execution trace, geometric validation,
    and standardized evaluation report.
    """
    problem = _resolve_problem(payload.problem_id, payload.problem)

    # Initialize CORELAP solver
    parameters = payload.config.model_dump() if payload.config else None
    solver: CORELAPAlgorithm = AlgorithmRegistry.get("corelap", parameters=parameters)  # type: ignore

    # Solve layout
    solution = solver.solve(problem)

    # Reconstruct continuous layout for validation and evaluation
    continuous_layout = ContinuousLayout.from_layout_solution(
        solution,
        facility_width=problem.facility.width,
        facility_height=problem.facility.height,
        reserved_zones=problem.facility.reserved_zones if hasattr(problem.facility, "reserved_zones") else None,
    )

    # Geometric validation
    validation = LayoutValidator.validate(problem, continuous_layout)

    # Evaluation via EvaluationEngine
    engine = EvaluationEngine()
    evaluation = engine.evaluate(problem=problem, solution=continuous_layout)

    # Extract execution trace
    trace_dict = solution.metadata.get("trace", {})
    trace = CORELAPExecutionTrace.model_validate(trace_dict)

    return CORELAPSolveResponse(
        solution=solution,
        continuous_layout=continuous_layout,
        trace=trace,
        validation=validation,
        evaluation=evaluation,
    )


@router.post(
    "/craft/solve",
    response_model=CRAFTSolveResponse,
    summary="Improve layout using CRAFT pairwise exchange heuristic",
)
def solve_craft(
    payload: CRAFTSolveRequest,
    _slot: Any = Depends(get_job_slot),
) -> CRAFTSolveResponse:
    """Run deterministic CRAFT pairwise exchange improvement heuristic on an existing layout.
    
    Validates initial layout completeness and feasibility, executes steepest-descent
    2-way department exchanges to minimize Material Handling Cost (MHC), and returns
    full before-and-after diagnostics.
    """
    problem = _resolve_problem(payload.problem_id, payload.problem)
    raw_initial = _resolve_initial_layout(payload.initial_layout_id, payload.initial_layout)

    # Verify and normalize initial layout
    try:
        norm_initial = _normalize_initial_layout(problem, raw_initial)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Configure CRAFT solver
    parameters = payload.config.model_dump() if payload.config else {}
    solver: CRAFTAlgorithm = AlgorithmRegistry.get("craft", parameters=parameters)  # type: ignore

    # Execute improvement search
    solution, result = solver.solve_with_result(problem, norm_initial, **parameters)

    # Standardized evaluation of before and after states
    eval_config = payload.evaluation_config or EvaluationConfig()
    eval_engine = EvaluationEngine(config=eval_config)
    initial_evaluation = eval_engine.evaluate(problem=problem, solution=norm_initial)
    final_evaluation = eval_engine.evaluate(problem=problem, solution=result.final_layout)

    return CRAFTSolveResponse(
        solution=solution,
        continuous_layout=result.final_layout,
        initial_layout=norm_initial,
        result=result,
        initial_evaluation=initial_evaluation,
        final_evaluation=final_evaluation,
        trace=result.trace,
    )


@router.post(
    "/aldep/solve",
    response_model=ALDEPSolveResponse,
    summary="Construct layout alternatives using ALDEP heuristic",
)
def solve_aldep(
    payload: ALDEPSolveRequest,
    _slot: Any = Depends(get_job_slot),
) -> ALDEPSolveResponse:
    """Run ALDEP (Automated Layout Design Program) stochastic construction heuristic.
    
    Generates multiple layout alternatives via Muther REL affinity and strip-sweep grid placement,
    ranks them via EvaluationEngine, and returns the top-ranked layout and candidate portfolio.
    """
    problem = _resolve_problem(payload.problem_id, payload.problem)

    parameters = payload.config.model_dump() if payload.config else {}
    solver: ALDEPAlgorithm = AlgorithmRegistry.get("aldep", parameters=parameters)  # type: ignore

    solution, result = solver.solve_with_result(problem, **parameters)

    # Validate and evaluate best candidate
    best_cont = result.best_candidate.continuous_layout
    validation = LayoutValidator.validate(problem, best_cont)
    eval_engine = EvaluationEngine()
    evaluation = eval_engine.evaluate(problem=problem, solution=best_cont)

    return ALDEPSolveResponse(
        solution=solution,
        continuous_layout=best_cont,
        grid_layout=result.best_candidate.grid_layout,
        best_candidate=result.best_candidate,
        candidates=result.candidates,
        result=result,
        trace=result.trace,
        validation=validation,
        evaluation=evaluation,
    )


class FeasibleGeneratorSolveRequest(BaseModel):
    """Payload to trigger Feasible Rectangular Layout Generator."""
    problem_id: Optional[str] = Field(None, description="Identifier of preloaded problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    config: Optional[GeneratorConfig] = Field(None, description="Generator search configuration")


class FeasibleGeneratorSolveResponse(BaseModel):
    """Standardized response from Feasible Layout Generator."""
    solution: Optional[LayoutSolution] = Field(None, description="Standardized layout solution")
    result: GeneratorResult = Field(..., description="Detailed generator search outcome and metrics")
    validation: Optional[LayoutValidationResult] = Field(None, description="Geometric validation outcome")
    evaluation: Optional[EvaluationReport] = Field(None, description="Multi-criteria evaluation report if complete")


@router.post(
    "/feasible-generator/solve",
    response_model=FeasibleGeneratorSolveResponse,
    summary="Generate feasible rectangular layout from scratch using constructive search",
)
def solve_feasible_generator(
    payload: FeasibleGeneratorSolveRequest,
    _slot: Any = Depends(get_job_slot),
) -> FeasibleGeneratorSolveResponse:
    """Generate constructible, non-overlapping, feasible rectangular layout without initial seed.
    
    Executes deterministic constructive search (Free Rectangle DFS or Guillotine Bay Packing)
    honoring area conservation, min/max dimensions, aspect ratios, fixed positions, and hard constraints.
    """
    problem = _resolve_problem(payload.problem_id, payload.problem)
    config = payload.config or GeneratorConfig()

    solver = FeasibleLayoutGenerator()
    solution, result = solver.solve_with_result(problem, config=config)

    validation: Optional[LayoutValidationResult] = None
    evaluation: Optional[EvaluationReport] = None

    if result.layout:
        validation = LayoutValidator.validate(problem, result.layout)
        if result.success and result.complete:
            eval_engine = EvaluationEngine()
            evaluation = eval_engine.evaluate(problem=problem, solution=result.layout)

    return FeasibleGeneratorSolveResponse(
        solution=solution,
        result=result,
        validation=validation,
        evaluation=evaluation,
    )


class GASolveRequest(BaseModel):
    """Payload to trigger Genetic Algorithm layout optimization."""

    problem_id: Optional[str] = Field(None, description="Identifier of preloaded problem")
    problem: Optional[Dict[str, Any]] = Field(None, description="Inline problem definition payload")
    config: Optional[GAConfig] = Field(None, description="Genetic Algorithm hyperparameter configuration")


class GASolveResponse(BaseModel):
    """Standardized response from Genetic Algorithm solver."""

    solution: LayoutSolution = Field(..., description="Best layout solution found")
    continuous_layout: ContinuousLayout = Field(..., description="Continuous layout representation")
    result: GAResult = Field(..., description="Detailed GA search outcome and convergence history")
    validation: LayoutValidationResult = Field(..., description="Geometric validation outcome")
    evaluation: EvaluationReport = Field(..., description="Evaluation report from EvaluationEngine")


@router.post(
    "/genetic/solve",
    response_model=GASolveResponse,
    summary="Optimize layout using Genetic Algorithm with Flexible Bay Structure",
)
def solve_genetic_algorithm(
    payload: GASolveRequest,
    _slot: Any = Depends(get_job_slot),
) -> GASolveResponse:
    """Optimize unequal-area facility layout using Genetic Algorithm.
    
    Uses Flexible Bay Structure (FBS) representation, Order Crossover (OX),
    and multi-objective fitness balancing Material Handling Cost (MHC) and soft constraints.
    """
    problem = _resolve_problem(payload.problem_id, payload.problem)
    config = payload.config or GAConfig()

    solver = GeneticLayoutAlgorithm()
    result = solver.solve_with_result(problem, config=config)

    validation = LayoutValidator.validate(problem, result.best_layout)
    eval_engine = EvaluationEngine()
    evaluation = eval_engine.evaluate(problem=problem, solution=result.best_layout)

    return GASolveResponse(
        solution=result.best_solution,
        continuous_layout=result.best_layout,
        result=result,
        validation=validation,
        evaluation=evaluation,
    )



