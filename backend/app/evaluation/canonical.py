"""Canonical evaluation service and standardized benchmark contract for FLODSS."""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.constraints.engine import ConstraintEngine
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.models.constraint import ConstraintClassification, ConstraintViolation
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.models.solution import LayoutSolution
from app.services.layout_normalizer import generate_layout_signature


def _sha256(text: str) -> str:
    """Deterministic SHA-256 hex digest helper."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_problem_provenance_hashes(problem: FacilityLayoutProblem) -> Dict[str, str]:
    """Compute component-level cryptographic provenance hashes for problem specification.
    
    Guarantees that benchmark scores are linked to immutable problem definitions:
    - department_geometry_hash: Facility bounds and all department area/aspect constraints
    - flow_matrix_hash: Pairwise flow volumes and unit costs
    - rel_matrix_hash: Muther closeness ratings and scores
    - constraint_definitions_hash: Hard/soft rules, required distances, and penalty rates
    - composite_data_hash: Master hash over all components
    """
    depts_str = "|".join(
        f"{d.id}:{d.required_area}:{d.min_width}:{d.max_width}:{d.min_height}:{d.max_height}:{d.min_aspect_ratio}:{d.max_aspect_ratio}"
        for d in sorted(problem.departments, key=lambda x: x.id)
    )
    fac_str = f"{problem.facility.width}x{problem.facility.height}|{depts_str}"
    dept_hash = _sha256(fac_str)

    flows_str = "|".join(
        f"{f.source_department}->{f.target_department}:{f.quantity}:{f.cost_per_unit_distance}"
        for f in sorted(problem.flows, key=lambda x: (x.source_department, x.target_department))
    )
    flow_hash = _sha256(flows_str)

    rels_str = "|".join(
        f"{r.department_a}<->{r.department_b}:{r.relationship_type.value}:{r.score}"
        for r in sorted(problem.relationships, key=lambda x: (x.department_a, x.department_b))
    )
    rel_hash = _sha256(rels_str)

    consts_str = "|".join(
        f"{c.id}:{c.type.value}:{sorted(c.involved_departments)}:{json.dumps(c.parameters, sort_keys=True)}:{c.classification.value}:{c.penalty}"
        for c in sorted(problem.constraints, key=lambda x: x.id)
    )
    const_hash = _sha256(consts_str)

    comp_str = f"{problem.id}|{dept_hash}|{flow_hash}|{rel_hash}|{const_hash}"
    composite_hash = _sha256(comp_str)

    return {
        "problem_id": problem.id,
        "composite_data_hash": composite_hash,
        "department_geometry_hash": dept_hash,
        "flow_matrix_hash": flow_hash,
        "rel_matrix_hash": rel_hash,
        "constraint_definitions_hash": const_hash,
    }


def compute_evaluation_config_hash(config: EvaluationConfig) -> str:
    """Compute deterministic SHA-256 hash of evaluation hyperparameters."""
    dump = config.model_dump()
    return _sha256(json.dumps(dump, sort_keys=True))


class CanonicalEvaluationReport(BaseModel):
    """Immutable, standardized evaluation report linking metrics to cryptographic data provenance."""

    # Provenance Fingerprints
    problem_id: str
    problem_composite_hash: str
    flow_matrix_hash: str
    rel_matrix_hash: str
    constraint_definitions_hash: str
    evaluation_config_hash: str
    layout_signature: str
    distance_metric: str
    engine_version: str = "1.0.0"

    # Core Academic & Industrial Metrics
    material_handling_cost: float = Field(..., description="Cost-weighted handling cost: Sum(F_ij * D_ij * C_ij) in USD ($)")
    flow_distance: float = Field(..., description="Unweighted volume distance: Sum(F_ij * D_ij) in m-moves")
    relationship_raw_score: float = Field(..., description="Net Muther proximity score: Sum(Reward) - Sum(Penalty)")
    relationship_satisfaction_percentage: float = Field(..., description="Normalized proximity satisfaction in [0.0, 100.0]%")
    area_utilization: float = Field(..., description="Floor space coverage: Total placed area / Usable facility area in %")

    # Constraints & Feasibility
    hard_violations_count: int = Field(default=0, ge=0)
    soft_violations_count: int = Field(default=0, ge=0)
    soft_penalty: float = Field(default=0.0, ge=0, description="Sum of soft constraint penalty costs in USD ($)")
    is_feasible: bool = Field(..., description="True if satisfies 100% of hard constraints and geometric validity")
    is_complete: bool = Field(..., description="True if all problem departments are placed")
    violations: List[Dict[str, Any]] = Field(default_factory=list)


class CanonicalEvaluationService:
    """Service implementing the formal evaluation contract for all benchmark layouts."""

    @classmethod
    def evaluate(
        cls,
        problem: FacilityLayoutProblem,
        solution: Union[ContinuousLayout, LayoutSolution, Dict[str, Any]],
        config: Optional[EvaluationConfig] = None,
    ) -> CanonicalEvaluationReport:
        """Evaluate a layout under canonical benchmark contract with complete provenance hashes."""
        eff_config = config or EvaluationConfig()
        engine = EvaluationEngine(config=eff_config)

        # Normalize layout
        if isinstance(solution, ContinuousLayout):
            layout = solution
        elif isinstance(solution, LayoutSolution):
            layout = ContinuousLayout.from_layout_solution(
                solution, problem.facility.width, problem.facility.height
            )
        elif isinstance(solution, dict):
            if "placements" in solution and solution["placements"] and isinstance(next(iter(solution["placements"].values())), dict):
                first_p = next(iter(solution["placements"].values()))
                if "origin" in first_p:
                    layout = ContinuousLayout.from_layout_solution(
                        solution, problem.facility.width, problem.facility.height
                    )
                else:
                    fw = solution.get("facility_width", problem.facility.width)
                    fh = solution.get("facility_height", problem.facility.height)
                    pid = solution.get("problem_id", problem.id)
                    placements = {
                        did: ContinuousPlacement(
                            department_id=did,
                            x=p["x"],
                            y=p["y"],
                            width=p["width"],
                            height=p["height"],
                            orientation_degrees=p.get("orientation_degrees", 0.0),
                        )
                        for did, p in solution["placements"].items()
                    }
                    layout = ContinuousLayout(
                        problem_id=pid,
                        facility_width=fw,
                        facility_height=fh,
                        placements=placements,
                    )
            else:
                layout = ContinuousLayout.model_validate(solution)
        else:
            raise TypeError(f"Unsupported layout type for canonical evaluation: {type(solution)}")

        # Execute centralized engine evaluation
        report = engine.evaluate(problem, layout, config=eff_config)

        # Compute provenance hashes
        prob_hashes = compute_problem_provenance_hashes(problem)
        cfg_hash = compute_evaluation_config_hash(eff_config)

        # Extract relationship satisfaction percentage
        rel_metric = report.metrics.get("relationship_satisfaction")
        rel_pct = rel_metric.value if rel_metric else 0.0

        violations_summary = [
            {
                "constraint_id": v.constraint_id,
                "classification": v.classification.value,
                "magnitude": v.magnitude,
                "penalty_cost": v.penalty_cost,
                "description": v.description or v.message,
            }
            for v in report.constraint_violations
        ]

        return CanonicalEvaluationReport(
            problem_id=problem.id,
            problem_composite_hash=prob_hashes["composite_data_hash"],
            flow_matrix_hash=prob_hashes["flow_matrix_hash"],
            rel_matrix_hash=prob_hashes["rel_matrix_hash"],
            constraint_definitions_hash=prob_hashes["constraint_definitions_hash"],
            evaluation_config_hash=cfg_hash,
            layout_signature=report.layout_signature or generate_layout_signature(layout),
            distance_metric=eff_config.distance_metric.value,
            engine_version=eff_config.engine_version,
            material_handling_cost=round(report.objective_values.get("material_handling_cost", 0.0), 2),
            flow_distance=round(report.objective_values.get("flow_distance", 0.0), 2),
            relationship_raw_score=round(report.objective_values.get("relationship_score", 0.0), 2),
            relationship_satisfaction_percentage=round(rel_pct, 2),
            area_utilization=round(report.objective_values.get("area_utilization", 0.0), 2),
            hard_violations_count=report.hard_violation_count,
            soft_violations_count=report.soft_violation_count,
            soft_penalty=round(report.total_constraint_penalty, 2),
            is_feasible=report.is_feasible,
            is_complete=report.complete_layout,
            violations=violations_summary,
        )
