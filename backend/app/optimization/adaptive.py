"""Adaptive Strategy Engine v1 for FLODSS.

Analyzes FacilityLayoutProblem characteristics, dynamically selects appropriate
algorithmic execution strategies (construction heuristics, exact rectangular generators,
metaheuristics, improvement algorithms), handles automatic fallbacks for incomplete or
infeasible results, manages resource budgets, maintains a shared deduplicated candidate portfolio,
and evaluates feasible candidates under canonical multi-objective Pareto frontier analysis.
"""

from enum import Enum
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.algorithms.aldep.solver import ALDEPAlgorithm
from app.algorithms.corelap.solver import CORELAPAlgorithm
from app.algorithms.craft.solver import CRAFTAlgorithm
from app.algorithms.ga.models import GAConfig
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.algorithms.generator.models import GeneratorConfig
from app.algorithms.generator.solver import FeasibleLayoutGenerator
from app.constraints.engine import ConstraintEngine
from app.evaluation.canonical import (
    CanonicalEvaluationReport,
    CanonicalEvaluationService,
    compute_evaluation_config_hash,
    compute_problem_provenance_hashes,
)
from app.evaluation.config import EvaluationConfig
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution
from app.optimization.pareto import (
    ObjectiveDefinition,
    ParetoAnalysisResult,
    ParetoCandidate,
    ParetoFrontierService,
    get_default_pareto_objectives,
)
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.services.problem_analyzer import ProblemAnalyzer, ProblemFingerprint

logger = logging.getLogger(__name__)


class StrategyArchetype(str, Enum):
    """Classification of problem archetype determining the strategy pipeline."""

    BASELINE_IMPROVEMENT = "baseline_improvement"
    DENSE_RECTANGULAR_CONSTRAINED = "dense_rectangular_constrained"
    REL_DOMINANT_GRID = "rel_dominant_grid"
    SMALL_UNCONSTRAINED_FLOW = "small_unconstrained_flow"
    FALLBACK_FEASIBLE = "fallback_feasible"


class StrategyPipeline(BaseModel):
    """Specification of an algorithm execution pipeline selected by rule-based heuristic."""

    archetype: StrategyArchetype
    name: str
    rule_id: str
    rule_description: str
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)
    primary_algorithm: str
    improvement_algorithms: List[str] = Field(default_factory=list)
    fallback_algorithm: Optional[str] = None
    rationale: str
    non_working_conditions: List[str] = Field(default_factory=list)


class AdaptiveConfig(BaseModel):
    """Resource budget and configuration limits for adaptive strategy execution."""

    max_total_runtime_seconds: float = Field(default=30.0, ge=0.5, description="Maximum total wall-clock budget (s)")
    max_algorithm_calls: int = Field(default=5, ge=1, description="Maximum number of individual algorithm executions")
    max_candidates: int = Field(default=20, ge=1, description="Maximum stored candidate layouts in portfolio")
    ga_population_size: int = Field(default=30, ge=4, description="Population size for GA improvement stages")
    ga_generations: int = Field(default=40, ge=1, description="Maximum generations for GA improvement stages")
    random_seed: int = Field(default=42, description="Base random seed for reproducible stochastic heuristics")
    fallback_enabled: bool = Field(default=True, description="Enable automatic fallback when primary method fails")


class DecisionTraceStep(BaseModel):
    """Structured explainable trace record of each algorithmic decision and execution step."""

    step_index: int
    action: str
    rule_id: Optional[str] = None
    rule_description: Optional[str] = None
    selected_algorithm: str
    algorithm_category: str
    parameters_used: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float
    success: bool
    is_complete: bool
    is_feasible: bool
    failure_reason: Optional[str] = None
    was_fallback: bool = False
    layout_signature: Optional[str] = None
    objective_values: Dict[str, float] = Field(default_factory=dict)
    next_action_rationale: str


class ProvenanceRecord(BaseModel):
    """Provenance tracking record for duplicate layout discovery across multiple algorithms."""

    algorithm_name: str
    algorithm_version: str
    random_seed: Optional[int] = None
    input_layout_signature: Optional[str] = None
    runtime_seconds: float
    step_index: int
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PortfolioCandidateItem(BaseModel):
    """A layout solution candidate maintained in the shared portfolio."""

    candidate_id: str
    source_algorithm: str
    source_version: str
    source_seed: Optional[int] = None
    input_layout_signature: Optional[str] = None
    output_layout_signature: str
    problem_hash: str
    evaluation_config_hash: str
    feasibility: bool
    completeness: bool
    material_handling_cost: Optional[float] = None
    relationship_satisfaction: Optional[float] = None
    soft_penalty: Optional[float] = None
    runtime_seconds: float
    trace: Dict[str, Any] = Field(default_factory=dict)
    rejection_reason: Optional[str] = None
    provenance_sources: List[ProvenanceRecord] = Field(default_factory=list)
    solution: Optional[LayoutSolution] = None


class CandidatePortfolio(BaseModel):
    """Portfolio of generated layout candidates with signature deduplication and provenance tracking."""

    total_candidates_generated: int = 0
    unique_candidates_count: int = 0
    feasible_candidates_count: int = 0
    infeasible_candidates_count: int = 0
    items: List[PortfolioCandidateItem] = Field(default_factory=list)
    deduplication_map: Dict[str, List[str]] = Field(default_factory=dict)  # signature -> list of algorithm names


class AdaptiveStrategyResult(BaseModel):
    """Comprehensive output of the Adaptive Strategy Engine."""

    problem_id: str
    fingerprint: ProblemFingerprint
    selected_strategy: StrategyPipeline
    execution_trace: List[DecisionTraceStep] = Field(default_factory=list)
    candidate_portfolio: CandidatePortfolio
    feasible_status: bool = Field(..., description="True if at least one complete feasible candidate was produced")
    canonical_evaluations: List[CanonicalEvaluationReport] = Field(default_factory=list)
    pareto_frontier: ParetoAnalysisResult
    final_recommendation: Optional[Dict[str, Any]] = None
    termination_reason: str
    total_runtime_seconds: float
    total_algorithm_calls: int


class RuleBasedStrategySelector:
    """Rule-based heuristic selector for facility layout optimization strategies.
    
    Academic & Engineering Principles:
    - Rule hypotheses are deterministic and explainable.
    - Thresholds are engineering heuristics based on facility planning literature (Muther, Tompkins, Armour).
    - Every rule explicitly defines its selection rationale and known failure/non-working conditions.
    """

    @classmethod
    def select_strategy(
        cls,
        fingerprint: ProblemFingerprint,
        has_initial_layout: bool = False,
    ) -> StrategyPipeline:
        """Evaluate problem fingerprint and return the matching strategy pipeline."""
        n = fingerprint.department_count
        util = fingerprint.area_utilization
        has_aspect = fingerprint.has_aspect_ratio_constraints
        has_dims = fingerprint.has_dimension_constraints
        fixed_count = fingerprint.fixed_departments_count
        res_count = fingerprint.reserved_zone_count
        rel_dens = fingerprint.rel_density
        flow_dens = fingerprint.flow_density

        # Rule D: Existing Baseline Layout Available
        if has_initial_layout:
            return StrategyPipeline(
                archetype=StrategyArchetype.BASELINE_IMPROVEMENT,
                name="Baseline Improvement Strategy",
                rule_id="RULE_BASELINE_IMPROVEMENT",
                rule_description="Complete initial layout is provided; apply pairwise exchange (CRAFT) and GA metaheuristic.",
                trigger_conditions={"has_initial_layout": True},
                primary_algorithm="craft",
                improvement_algorithms=["genetic_algorithm"],
                fallback_algorithm="feasible_layout_generator",
                rationale="An existing complete layout exists. Running CRAFT local search followed by GA exploration refines flow efficiency without discarding baseline structure.",
                non_working_conditions=[
                    "Initial layout is geometrically invalid or contains overlapping departments.",
                    "Departments have fixed positions that prevent pairwise swapping.",
                ],
            )

        # Rule C: REL-Dominant Grid Problems
        # Closeness matrix dominates over flows, low flow density, unconstrained aspect bounds
        if rel_dens >= 0.35 and flow_dens <= 0.20 and not has_aspect and res_count == 0:
            return StrategyPipeline(
                archetype=StrategyArchetype.REL_DOMINANT_GRID,
                name="ALDEP Strip-Sweep Construction + CRAFT Improvement",
                rule_id="RULE_REL_DOMINANT_GRID",
                rule_description="High relationship density (rel_density >= 0.35), sparse flow matrix (flow_density <= 0.20), and relaxed aspect bounds; use ALDEP strip-sweep.",
                trigger_conditions={
                    "rel_density": rel_dens,
                    "flow_density": flow_dens,
                    "has_aspect_ratio_constraints": has_aspect,
                    "reserved_zone_count": res_count,
                },
                primary_algorithm="aldep",
                improvement_algorithms=["craft"],
                fallback_algorithm="feasible_layout_generator",
                rationale="Qualitative closeness ratings dominate over handling flows. ALDEP clusters high-affinity departments along a continuous sweep pattern. If continuous geometric validation fails, fallback to FeasibleLayoutGenerator.",
                non_working_conditions=[
                    "Strict rectangular aspect ratio requirements (ALDEP may produce serpentine or non-rectangular shapes).",
                    "Obstacle zones or reserved corridors exist inside the facility.",
                ],
            )

        # Rule A: Small / Low-Density Unconstrained Problems (N <= 6, area utilization < 0.80, no obstacles)
        if n <= 6 and util < 0.80 and fixed_count == 0 and res_count == 0:
            return StrategyPipeline(
                archetype=StrategyArchetype.SMALL_UNCONSTRAINED_FLOW,
                name="CORELAP Construction + CRAFT Pairwise Improvement",
                rule_id="RULE_SMALL_UNCONSTRAINED_FLOW",
                rule_description="Small problem (N <= 6), moderate floor utilization (< 0.80), and no fixed/reserved obstacles; use classical CORELAP greedy construction.",
                trigger_conditions={
                    "department_count": n,
                    "area_utilization": util,
                    "fixed_departments_count": fixed_count,
                    "reserved_zone_count": res_count,
                },
                primary_algorithm="corelap",
                improvement_algorithms=["craft"],
                fallback_algorithm="feasible_layout_generator",
                rationale="Small unconstrained layouts (e.g. FLP_ACADEMIC_4, FLP_LOGISTICS_5) are efficiently constructed by CORELAP's Total Closeness Rating (TCR) ordering and spiral placement, followed by CRAFT pairwise exchange.",
                non_working_conditions=[
                    "High area utilization causes CORELAP spiral placement to exceed facility perimeter.",
                    "Complex fixed positions or reserved zones block spiral growth.",
                ],
            )

        # Rule B: Dense / Strict Rectangular Constrained Problems
        # Default for dense, multi-department, or highly constrained industrial layouts
        return StrategyPipeline(
            archetype=StrategyArchetype.DENSE_RECTANGULAR_CONSTRAINED,
            name="Feasible Rectangular Construction + GA Metaheuristic",
            rule_id="RULE_DENSE_RECTANGULAR_CONSTRAINED",
            rule_description="High area density (utilization >= 0.80), N >= 7, or strict fixed/reserved/aspect constraints; utilize exact Guillotine Row Packing then GA optimization.",
            trigger_conditions={
                "department_count": n,
                "area_utilization": util,
                "has_aspect_ratio_constraints": has_aspect,
                "has_dimension_constraints": has_dims,
                "fixed_departments_count": fixed_count,
                "reserved_zone_count": res_count,
            },
            primary_algorithm="feasible_layout_generator",
            improvement_algorithms=["genetic_algorithm"],
            fallback_algorithm="genetic_algorithm",
            rationale="Dense factory footprints with strict aspect bounds (e.g. FLP_INDUSTRIAL_10, FLP_EXPANSION_8) cause classical greedy heuristics to fail. FeasibleLayoutGenerator guarantees exact boundary containment, followed by GA Flexible Bay Structure exploration.",
            non_working_conditions=[
                "Total department area exceeds facility boundary (area utilization > 1.0).",
                "Department aspect ratio bounds are mathematically incompatible with facility bounding dimensions.",
            ],
        )


def _to_continuous_layout(
    problem: FacilityLayoutProblem,
    solution: Union[LayoutSolution, ContinuousLayout, Dict[str, Any]],
) -> ContinuousLayout:
    """Ensure layout is in ContinuousLayout format for geometric operations."""
    if isinstance(solution, ContinuousLayout):
        return solution
    if isinstance(solution, LayoutSolution):
        return ContinuousLayout.from_layout_solution(
            solution,
            facility_width=problem.facility.width,
            facility_height=problem.facility.height,
            reserved_zones=getattr(problem.facility, "reserved_zones", None),
        )
    if isinstance(solution, dict):
        return ContinuousLayout.model_validate(solution)
    raise ValueError(f"Unsupported layout type: {type(solution)}")


class StrategyExecutionEngine:
    """Executes the adaptive strategy pipeline with resource budgeting, fallback handling, and portfolio management."""

    @classmethod
    def execute(
        cls,
        problem: FacilityLayoutProblem,
        config: Optional[AdaptiveConfig] = None,
        initial_layout: Optional[Union[ContinuousLayout, LayoutSolution, Dict[str, Any]]] = None,
        evaluation_config: Optional[EvaluationConfig] = None,
    ) -> AdaptiveStrategyResult:
        """Run adaptive optimization with strict budgeting, validation, and explainable decision tracing."""
        start_time = time.perf_counter()
        cfg = config or AdaptiveConfig()
        eval_cfg = evaluation_config or EvaluationConfig()

        # Step 1: Extract Fingerprint
        fingerprint = ProblemAnalyzer.extract_fingerprint(problem)

        # Step 2: Select Strategy Pipeline
        has_init = initial_layout is not None
        strategy = RuleBasedStrategySelector.select_strategy(fingerprint, has_initial_layout=has_init)

        # State Tracking
        trace_steps: List[DecisionTraceStep] = []
        portfolio = CandidatePortfolio()
        algorithm_calls_count = 0
        latest_feasible_solution: Optional[LayoutSolution] = None
        termination_reason = "COMPLETED_SUCCESSFULLY"

        def get_elapsed() -> float:
            return round(time.perf_counter() - start_time, 4)

        def get_remaining_time() -> float:
            rem = cfg.max_total_runtime_seconds - (time.perf_counter() - start_time)
            return max(0.1, round(rem, 3))

        def can_call_algorithm() -> Tuple[bool, Optional[str]]:
            if time.perf_counter() - start_time >= cfg.max_total_runtime_seconds:
                return False, "TIME_BUDGET_EXHAUSTED"
            if algorithm_calls_count >= cfg.max_algorithm_calls:
                return False, "CALL_LIMIT_REACHED"
            if len(portfolio.items) >= cfg.max_candidates:
                return False, "CANDIDATE_LIMIT_REACHED"
            return True, None

        # Provenance Hashes
        prob_hashes = compute_problem_provenance_hashes(problem)
        problem_hash = prob_hashes["composite_data_hash"]
        eval_cfg_hash = compute_evaluation_config_hash(eval_cfg)

        def register_solution(
            algo_name: str,
            algo_version: str,
            seed: Optional[int],
            solution: LayoutSolution,
            runtime: float,
            input_sig: Optional[str] = None,
            trace_metadata: Optional[Dict[str, Any]] = None,
        ) -> Tuple[PortfolioCandidateItem, bool, bool, Optional[CanonicalEvaluationReport]]:
            """Validate, canonically evaluate, and register a candidate in the portfolio with deduplication."""
            nonlocal portfolio

            # Independent validation
            val_res = LayoutValidator.validate(problem, solution)
            const_engine = ConstraintEngine()
            violations = const_engine.check_all(problem, solution)
            is_const_valid = ConstraintEngine.is_feasible(violations)

            is_complete = bool(solution.is_complete and len(solution.placements) == len(problem.departments))
            is_geom_valid = bool(val_res.is_valid)
            is_feasible = is_complete and is_geom_valid and is_const_valid

            sig = solution.metadata.get("layout_signature")
            if not sig:
                try:
                    cont = _to_continuous_layout(problem, solution)
                    sig = generate_layout_signature(cont)
                except Exception:
                    sig = hashlib.sha256(str(sorted(solution.placements.keys())).encode("utf-8")).hexdigest()

            portfolio.total_candidates_generated += 1

            canon_report: Optional[CanonicalEvaluationReport] = None
            mhc: Optional[float] = None
            rel_sat: Optional[float] = None
            soft_pen: Optional[float] = None
            rejection_reason: Optional[str] = None

            if is_feasible:
                canon_report = CanonicalEvaluationService.evaluate(problem, solution, config=eval_cfg)
                mhc = canon_report.material_handling_cost
                rel_sat = canon_report.relationship_satisfaction_percentage
                soft_pen = canon_report.soft_penalty
            else:
                rejection_parts = []
                if not is_complete:
                    rejection_parts.append(f"Incomplete: {len(solution.placements)}/{len(problem.departments)} placed")
                if not is_geom_valid:
                    rejection_parts.append(f"Geometry invalid: {'; '.join(val_res.errors[:2])}")
                if not is_const_valid:
                    hard_cnt = ConstraintEngine.count_hard_violations(violations)
                    rejection_parts.append(f"Constraints violated: {hard_cnt} hard violations")
                rejection_reason = " | ".join(rejection_parts)

            # Deduplication by layout signature
            prov_rec = ProvenanceRecord(
                algorithm_name=algo_name,
                algorithm_version=algo_version,
                random_seed=seed,
                input_layout_signature=input_sig,
                runtime_seconds=runtime,
                step_index=len(trace_steps) + 1,
                parameters=dict(trace_metadata) if trace_metadata else {},
            )

            if sig in portfolio.deduplication_map:
                # Signature already seen; locate item and append provenance
                existing_item = next((it for it in portfolio.items if it.output_layout_signature == sig), None)
                if existing_item:
                    existing_item.provenance_sources.append(prov_rec)
                    portfolio.deduplication_map[sig].append(algo_name)
                    return existing_item, is_feasible, is_complete, canon_report

            # New unique layout candidate
            cand_id = f"cand_{len(portfolio.items) + 1}"
            new_item = PortfolioCandidateItem(
                candidate_id=cand_id,
                source_algorithm=algo_name,
                source_version=algo_version,
                source_seed=seed,
                input_layout_signature=input_sig,
                output_layout_signature=sig,
                problem_hash=problem_hash,
                evaluation_config_hash=eval_cfg_hash,
                feasibility=is_feasible,
                completeness=is_complete,
                material_handling_cost=mhc,
                relationship_satisfaction=rel_sat,
                soft_penalty=soft_pen,
                runtime_seconds=runtime,
                trace=trace_metadata or {},
                rejection_reason=rejection_reason,
                provenance_sources=[prov_rec],
                solution=solution,
            )

            portfolio.items.append(new_item)
            portfolio.deduplication_map[sig] = [algo_name]
            portfolio.unique_candidates_count = len(portfolio.items)
            if is_feasible:
                portfolio.feasible_candidates_count += 1
            else:
                portfolio.infeasible_candidates_count += 1

            return new_item, is_feasible, is_complete, canon_report

        def run_algorithm(
            algo_key: str,
            is_fallback: bool = False,
            seed: int = 42,
            init_layout: Optional[Any] = None,
        ) -> Tuple[Optional[LayoutSolution], float, Optional[str]]:
            """Instantiate and execute an algorithm under strict remaining time budget."""
            nonlocal algorithm_calls_count
            algorithm_calls_count += 1
            rem_time = get_remaining_time()
            t0 = time.perf_counter()
            err_msg: Optional[str] = None
            sol: Optional[LayoutSolution] = None

            try:
                if algo_key in ["feasible_layout_generator", "feasible_generator"]:
                    res_zones = getattr(problem.facility, "reserved_zones", []) or []
                    if len(res_zones) > 0:
                        gen_strat = "free_rectangle_dfs"
                    elif fingerprint.area_utilization >= 0.85:
                        gen_strat = "guillotine_row_packing"
                    else:
                        gen_strat = "free_rectangle_dfs"

                    gen = FeasibleLayoutGenerator(parameters={
                        "strategy": gen_strat,
                        "max_runtime_seconds": rem_time,
                        "random_seed": seed,
                    })
                    sol = gen.solve(problem)
                    if not sol.is_complete or not sol.feasibility_status:
                        alt_strat = "free_rectangle_dfs" if gen_strat == "guillotine_row_packing" else "guillotine_row_packing"
                        gen_alt = FeasibleLayoutGenerator(parameters={
                            "strategy": alt_strat,
                            "max_runtime_seconds": rem_time,
                            "random_seed": seed,
                        })
                        sol_alt = gen_alt.solve(problem)
                        if sol_alt.is_complete and sol_alt.feasibility_status:
                            sol = sol_alt
                elif algo_key in ["corelap"]:
                    corelap = CORELAPAlgorithm()
                    sol = corelap.solve(problem)
                elif algo_key in ["aldep"]:
                    aldep = ALDEPAlgorithm(parameters={"random_seed": seed})
                    res = aldep.solve(problem)
                    sol = res[0] if isinstance(res, tuple) else res
                elif algo_key in ["craft", "craft_pairwise_rectangular_v1"]:
                    craft = CRAFTAlgorithm(parameters={"max_iterations": 25})
                    if init_layout is not None:
                        res = craft.improve(problem, initial_layout=init_layout)
                    else:
                        raise ValueError("CRAFT requires a valid initial layout.")
                    sol = res[0] if isinstance(res, tuple) else res
                elif algo_key in ["genetic_algorithm", "ga"]:
                    ga = GeneticLayoutAlgorithm(parameters={
                        "max_runtime_seconds": rem_time,
                        "population_size": cfg.ga_population_size,
                        "generations": cfg.ga_generations,
                        "random_seed": seed,
                    })
                    sol = ga.solve(problem)
                else:
                    err_msg = f"Unknown algorithm identifier: '{algo_key}'"
            except Exception as ex:
                logger.warning("Algorithm '%s' raised exception: %s", algo_key, ex)
                err_msg = str(ex)

            exec_time = round(time.perf_counter() - t0, 4)
            return sol, exec_time, err_msg

        # =========================================================================
        # Stage 1: Run Primary Algorithm
        # =========================================================================
        can_run, budget_reason = can_call_algorithm()
        primary_success = False

        if not can_run:
            termination_reason = budget_reason or "BUDGET_EXHAUSTED"
        else:
            primary_algo = strategy.primary_algorithm
            sol, run_sec, err = run_algorithm(
                algo_key=primary_algo,
                is_fallback=False,
                seed=cfg.random_seed,
                init_layout=initial_layout if primary_algo == "craft" else None,
            )

            if sol is not None:
                item, is_feas, is_comp, canon = register_solution(
                    algo_name=primary_algo,
                    algo_version="1.0.0",
                    seed=cfg.random_seed,
                    solution=sol,
                    runtime=run_sec,
                    trace_metadata=sol.metadata,
                )
                primary_success = is_feas
                if is_feas:
                    latest_feasible_solution = sol

                step_trace = DecisionTraceStep(
                    step_index=len(trace_steps) + 1,
                    action=f"EXECUTE_PRIMARY_{primary_algo.upper()}",
                    rule_id=strategy.rule_id,
                    rule_description=strategy.rule_description,
                    selected_algorithm=primary_algo,
                    algorithm_category="primary",
                    parameters_used={"random_seed": cfg.random_seed, "remaining_time_budget": get_remaining_time()},
                    execution_time_seconds=run_sec,
                    success=is_feas,
                    is_complete=is_comp,
                    is_feasible=is_feas,
                    failure_reason=item.rejection_reason if not is_feas else None,
                    was_fallback=False,
                    layout_signature=item.output_layout_signature,
                    objective_values={
                        "material_handling_cost": item.material_handling_cost or 0.0,
                        "relationship_satisfaction": item.relationship_satisfaction or 0.0,
                        "soft_penalty": item.soft_penalty or 0.0,
                    } if is_feas else {},
                    next_action_rationale="Primary algorithm completed successfully; proceed to improvement."
                    if is_feas else "Primary algorithm produced incomplete/infeasible layout; triggering fallback."
                )
                trace_steps.append(step_trace)
            else:
                primary_success = False
                step_trace = DecisionTraceStep(
                    step_index=len(trace_steps) + 1,
                    action=f"EXECUTE_PRIMARY_{primary_algo.upper()}",
                    rule_id=strategy.rule_id,
                    rule_description=strategy.rule_description,
                    selected_algorithm=primary_algo,
                    algorithm_category="primary",
                    parameters_used={"random_seed": cfg.random_seed},
                    execution_time_seconds=run_sec,
                    success=False,
                    is_complete=False,
                    is_feasible=False,
                    failure_reason=err or "Execution failed without solution.",
                    was_fallback=False,
                    next_action_rationale="Execution error occurred; triggering fallback."
                )
                trace_steps.append(step_trace)

        # =========================================================================
        # Stage 2: Automatic Fallback Execution (if primary failed and enabled)
        # =========================================================================
        if not primary_success and cfg.fallback_enabled and strategy.fallback_algorithm:
            can_run, budget_reason = can_call_algorithm()
            if not can_run:
                termination_reason = budget_reason or "BUDGET_EXHAUSTED_BEFORE_FALLBACK"
                trace_steps.append(DecisionTraceStep(
                    step_index=len(trace_steps) + 1,
                    action="FALLBACK_SKIPPED",
                    rule_id=strategy.rule_id,
                    selected_algorithm=strategy.fallback_algorithm,
                    algorithm_category="fallback",
                    parameters_used={},
                    execution_time_seconds=0.0,
                    success=False,
                    is_complete=False,
                    is_feasible=False,
                    failure_reason=budget_reason or "Budget exhausted before fallback could run.",
                    was_fallback=True,
                    next_action_rationale="Cannot trigger fallback due to resource exhaustion."
                ))
            else:
                fallback_algo = strategy.fallback_algorithm
                fb_sol, fb_sec, fb_err = run_algorithm(
                    algo_key=fallback_algo,
                    is_fallback=True,
                    seed=cfg.random_seed + 1,
                )

                if fb_sol is not None:
                    fb_item, fb_feas, fb_comp, fb_canon = register_solution(
                        algo_name=fallback_algo,
                        algo_version="1.0.0",
                        seed=cfg.random_seed + 1,
                        solution=fb_sol,
                        runtime=fb_sec,
                        trace_metadata=fb_sol.metadata,
                    )
                    if fb_feas:
                        latest_feasible_solution = fb_sol

                    trace_steps.append(DecisionTraceStep(
                        step_index=len(trace_steps) + 1,
                        action=f"EXECUTE_FALLBACK_{fallback_algo.upper()}",
                        rule_id=strategy.rule_id,
                        selected_algorithm=fallback_algo,
                        algorithm_category="fallback",
                        parameters_used={"random_seed": cfg.random_seed + 1, "remaining_time_budget": get_remaining_time()},
                        execution_time_seconds=fb_sec,
                        success=fb_feas,
                        is_complete=fb_comp,
                        is_feasible=fb_feas,
                        failure_reason=fb_item.rejection_reason if not fb_feas else None,
                        was_fallback=True,
                        layout_signature=fb_item.output_layout_signature,
                        objective_values={
                            "material_handling_cost": fb_item.material_handling_cost or 0.0,
                            "relationship_satisfaction": fb_item.relationship_satisfaction or 0.0,
                            "soft_penalty": fb_item.soft_penalty or 0.0,
                        } if fb_feas else {},
                        next_action_rationale="Fallback succeeded in finding feasible layout." if fb_feas
                        else "Fallback also failed to produce feasible layout."
                    ))
                else:
                    trace_steps.append(DecisionTraceStep(
                        step_index=len(trace_steps) + 1,
                        action=f"EXECUTE_FALLBACK_{fallback_algo.upper()}",
                        rule_id=strategy.rule_id,
                        selected_algorithm=fallback_algo,
                        algorithm_category="fallback",
                        parameters_used={},
                        execution_time_seconds=fb_sec,
                        success=False,
                        is_complete=False,
                        is_feasible=False,
                        failure_reason=fb_err or "Fallback execution failed.",
                        was_fallback=True,
                        next_action_rationale="Fallback failed."
                    ))

        # =========================================================================
        # Stage 3: Improvement Algorithms (if feasible solution exists)
        # =========================================================================
        if latest_feasible_solution is not None:
            for imp_algo in strategy.improvement_algorithms:
                can_run, budget_reason = can_call_algorithm()
                if not can_run:
                    logger.info("Stopping improvement stages due to budget limit: %s", budget_reason)
                    if termination_reason == "COMPLETED_SUCCESSFULLY":
                        termination_reason = budget_reason or "IMPROVEMENT_BUDGET_LIMIT"
                    break

                init_sig = latest_feasible_solution.metadata.get("layout_signature")
                if not init_sig:
                    try:
                        init_sig = generate_layout_signature(_to_continuous_layout(problem, latest_feasible_solution))
                    except Exception:
                        init_sig = None

                imp_sol, imp_sec, imp_err = run_algorithm(
                    algo_key=imp_algo,
                    is_fallback=False,
                    seed=cfg.random_seed + 2,
                    init_layout=latest_feasible_solution if imp_algo == "craft" else None,
                )

                if imp_sol is not None:
                    imp_item, imp_feas, imp_comp, imp_canon = register_solution(
                        algo_name=imp_algo,
                        algo_version="1.0.0",
                        seed=cfg.random_seed + 2,
                        solution=imp_sol,
                        runtime=imp_sec,
                        input_sig=init_sig,
                        trace_metadata=imp_sol.metadata,
                    )
                    if imp_feas:
                        latest_feasible_solution = imp_sol

                    trace_steps.append(DecisionTraceStep(
                        step_index=len(trace_steps) + 1,
                        action=f"EXECUTE_IMPROVEMENT_{imp_algo.upper()}",
                        rule_id=strategy.rule_id,
                        selected_algorithm=imp_algo,
                        algorithm_category="improvement",
                        parameters_used={"random_seed": cfg.random_seed + 2, "remaining_time_budget": get_remaining_time()},
                        execution_time_seconds=imp_sec,
                        success=imp_feas,
                        is_complete=imp_comp,
                        is_feasible=imp_feas,
                        failure_reason=imp_item.rejection_reason if not imp_feas else None,
                        was_fallback=False,
                        layout_signature=imp_item.output_layout_signature,
                        objective_values={
                            "material_handling_cost": imp_item.material_handling_cost or 0.0,
                            "relationship_satisfaction": imp_item.relationship_satisfaction or 0.0,
                            "soft_penalty": imp_item.soft_penalty or 0.0,
                        } if imp_feas else {},
                        next_action_rationale=f"Improvement stage with {imp_algo} evaluated."
                    ))

        # =========================================================================
        # Stage 4: Canonical Multi-Objective Evaluation & Pareto Analysis
        # =========================================================================
        # Only feasible candidates enter Pareto analysis
        feasible_items = [it for it in portfolio.items if it.feasibility and it.solution is not None]
        canonical_reports: List[CanonicalEvaluationReport] = []
        pareto_raw_candidates: List[ParetoCandidate] = []

        for item in feasible_items:
            rep = CanonicalEvaluationService.evaluate(problem, item.solution, config=eval_cfg)
            canonical_reports.append(rep)
            cand = ParetoCandidate(
                candidate_id=item.candidate_id,
                algorithm_source=item.source_algorithm,
                layout_signature=rep.layout_signature,
                problem_id=rep.problem_id,
                problem_composite_hash=rep.problem_composite_hash,
                evaluation_config_hash=rep.evaluation_config_hash,
                objective_values={
                    "material_handling_cost": rep.material_handling_cost,
                    "relationship_satisfaction": rep.relationship_satisfaction_percentage,
                    "soft_penalty": rep.soft_penalty,
                },
                auxiliary_metrics={
                    "flow_distance": rep.flow_distance,
                    "relationship_raw_score": rep.relationship_raw_score,
                    "area_utilization": rep.area_utilization,
                    "runtime_seconds": item.runtime_seconds,
                },
                is_complete=rep.is_complete,
                is_feasible=rep.is_feasible,
                hard_violations_count=rep.hard_violations_count,
                soft_violations_count=rep.soft_violations_count,
                soft_penalty_cost=rep.soft_penalty,
                violations=rep.violations,
                placements=item.solution.placements if hasattr(item.solution, "placements") else {},
            )
            pareto_raw_candidates.append(cand)

        pareto_result = ParetoFrontierService.analyze(
            problem=problem,
            raw_candidates=pareto_raw_candidates,
            config=eval_cfg,
        )

        has_feasible = len(feasible_items) > 0
        final_rec: Optional[Dict[str, Any]] = None

        if has_feasible and pareto_result.valid_candidates_count > 0:
            # Recommendation: Find best candidate (highest balanced utility or lowest MHC)
            best_cand = None
            if "balanced" in pareto_result.recommendations:
                rec_id = pareto_result.recommendations["balanced"].recommended_candidate_id
                best_cand = next((c for c in pareto_result.candidates if c.candidate_id == rec_id), None)
            if best_cand is None and pareto_result.candidates:
                # Lowest MHC among non-dominated
                non_dom = [c for c in pareto_result.candidates if c.is_non_dominated]
                target_pool = non_dom if non_dom else pareto_result.candidates
                best_cand = min(target_pool, key=lambda c: c.objective_values.get("material_handling_cost", float("inf")))

            if best_cand:
                # Find matching portfolio item
                matching_item = next(
                    (it for it in feasible_items if it.candidate_id == best_cand.candidate_id or it.output_layout_signature == best_cand.layout_signature),
                    None
                )
                final_rec = {
                    "candidate_id": best_cand.candidate_id,
                    "layout_signature": best_cand.layout_signature,
                    "source_algorithm": best_cand.algorithm_source,
                    "provenance_algorithms": matching_item.provenance_sources if matching_item else [],
                    "material_handling_cost": best_cand.objective_values.get("material_handling_cost"),
                    "relationship_satisfaction": best_cand.objective_values.get("relationship_satisfaction"),
                    "soft_penalty": best_cand.objective_values.get("soft_penalty"),
                    "is_on_pareto_frontier": best_cand.is_non_dominated,
                    "pareto_rank": best_cand.pareto_rank,
                    "utility_score": best_cand.normalized_utility,
                    "best_layout_solution": matching_item.solution.model_dump(mode="json") if matching_item and matching_item.solution else None,
                }
        else:
            if not has_feasible:
                termination_reason = "NO_FEASIBLE_SOLUTION_FOUND"

        total_runtime = get_elapsed()

        return AdaptiveStrategyResult(
            problem_id=problem.id,
            fingerprint=fingerprint,
            selected_strategy=strategy,
            execution_trace=trace_steps,
            candidate_portfolio=portfolio,
            feasible_status=has_feasible,
            canonical_evaluations=canonical_reports,
            pareto_frontier=pareto_result,
            final_recommendation=final_rec,
            termination_reason=termination_reason,
            total_runtime_seconds=total_runtime,
            total_algorithm_calls=algorithm_calls_count,
        )
