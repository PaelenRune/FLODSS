"""Phase 9.2: Evaluation Integrity & Reproducibility Audit Runner."""

import hashlib
import json
import math
import os
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.ga.models import GAConfig, GAResult
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.constraints.engine import ConstraintEngine
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.evaluation.evaluators import MaterialHandlingCostEvaluator, FlowDistanceEvaluator
from app.feasibility.service import RectangularFeasibilityService
from app.models.constraint import ConstraintClassification
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.geometry_engine import DistanceMetricType, GeometryEngine
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.services.problem_service import problem_service


def compute_sha256(data_str: str) -> str:
    """Compute deterministic SHA-256 hex digest."""
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()


def compute_problem_hashes(problem: FacilityLayoutProblem) -> Dict[str, str]:
    """Compute component-level cryptographic provenance hashes for problem data."""
    # 1. Facility & Department Geometry definitions
    depts_str = "|".join(
        f"{d.id}:{d.required_area}:{d.min_width}:{d.max_width}:{d.min_height}:{d.max_height}:{d.min_aspect_ratio}:{d.max_aspect_ratio}"
        for d in sorted(problem.departments, key=lambda x: x.id)
    )
    fac_str = f"{problem.facility.width}x{problem.facility.height}|{depts_str}"
    dept_hash = compute_sha256(fac_str)

    # 2. Flow Matrix
    flows_str = "|".join(
        f"{f.source_department}->{f.target_department}:{f.quantity}:{f.cost_per_unit_distance}"
        for f in sorted(problem.flows, key=lambda x: (x.source_department, x.target_department))
    )
    flow_hash = compute_sha256(flows_str)

    # 3. Relationship (REL) Matrix
    rels_str = "|".join(
        f"{r.department_a}<->{r.department_b}:{r.relationship_type.value}:{r.score}"
        for r in sorted(problem.relationships, key=lambda x: (x.department_a, x.department_b))
    )
    rel_hash = compute_sha256(rels_str)

    # 4. Constraint Definitions
    consts_str = "|".join(
        f"{c.id}:{c.type.value}:{sorted(c.involved_departments)}:{json.dumps(c.parameters, sort_keys=True)}:{c.classification.value}:{c.penalty}"
        for c in sorted(problem.constraints, key=lambda x: x.id)
    )
    const_hash = compute_sha256(consts_str)

    # 5. Composite Problem Data Hash
    comp_str = f"{problem.id}|{dept_hash}|{flow_hash}|{rel_hash}|{const_hash}"
    composite_hash = compute_sha256(comp_str)

    return {
        "problem_id": problem.id,
        "composite_data_hash": composite_hash,
        "department_geometry_hash": dept_hash,
        "flow_matrix_hash": flow_hash,
        "rel_matrix_hash": rel_hash,
        "constraint_definitions_hash": const_hash,
    }


def compute_config_hash(config: EvaluationConfig) -> str:
    """Compute SHA-256 fingerprint of evaluation configuration."""
    cfg_dump = config.model_dump()
    cfg_str = json.dumps(cfg_dump, sort_keys=True)
    return compute_sha256(cfg_str)


def evaluate_canonical(
    problem: FacilityLayoutProblem,
    layout: ContinuousLayout,
    config: Optional[EvaluationConfig] = None,
) -> Dict[str, Any]:
    """Execute canonical standardized evaluation with complete provenance metadata."""
    cfg = config or EvaluationConfig()
    engine = EvaluationEngine(config=cfg)
    prob_hashes = compute_problem_hashes(problem)
    cfg_hash = compute_config_hash(cfg)
    sig = generate_layout_signature(layout)

    rep = engine.evaluate(problem, layout, config=cfg)
    rel_pct = rep.metrics.get("relationship_satisfaction").value if "relationship_satisfaction" in rep.metrics else 0.0

    return {
        "problem_id": problem.id,
        "layout_signature": sig,
        "evaluation_config_hash": cfg_hash,
        "problem_composite_hash": prob_hashes["composite_data_hash"],
        "flow_matrix_hash": prob_hashes["flow_matrix_hash"],
        "rel_matrix_hash": prob_hashes["rel_matrix_hash"],
        "constraint_definitions_hash": prob_hashes["constraint_definitions_hash"],
        "distance_metric": cfg.distance_metric.value,
        "material_handling_cost": round(rep.objective_values.get("material_handling_cost", 0.0), 2),
        "flow_distance": round(rep.objective_values.get("flow_distance", 0.0), 2),
        "relationship_raw_score": round(rep.objective_values.get("relationship_score", 0.0), 2),
        "relationship_satisfaction_percentage": round(rel_pct, 2),
        "area_utilization": round(rep.objective_values.get("area_utilization", 0.0), 2),
        "hard_violations_count": rep.hard_violation_count,
        "soft_violations_count": rep.soft_violation_count,
        "soft_penalty": round(rep.total_constraint_penalty, 2),
        "is_feasible": rep.is_feasible,
        "is_complete": rep.complete_layout,
        "violations": [
            {
                "constraint_id": v.constraint_id,
                "classification": v.classification.value,
                "magnitude": v.magnitude,
                "penalty_cost": v.penalty_cost,
                "message": v.message or v.description,
            }
            for v in rep.constraint_violations
        ],
    }


def run_audit():
    problem = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    print("=================================================================")
    print("PHASE 9.2: EVALUATION INTEGRITY & REPRODUCIBILITY AUDIT")
    print("=================================================================\n")

    # 1. Problem Provenance Hashes
    prob_hashes = compute_problem_hashes(problem)
    print("1. Problem Data Provenance Hashes:")
    for k, v in prob_hashes.items():
        print(f"   {k:28s}: {v}")

    # 2. Canonical Evaluation of the 3 Saved Layouts
    print("\n2. Canonical Evaluation of Saved Layouts:")
    layouts_info = [
        ("Manual Baseline", "data/examples/sample_layout.json"),
        ("Guillotine Baseline", "data/examples/generated_industrial_10.json"),
        ("GA Best Solution", "data/examples/ga_optimized_industrial_10.json"),
    ]

    canonical_results = {}
    for name, path in layouts_info:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if "placements" in d and isinstance(next(iter(d["placements"].values())), dict) and "origin" in next(iter(d["placements"].values())):
            layout = ContinuousLayout.from_layout_solution(d, problem.facility.width, problem.facility.height)
        elif "placements" in d and "x" in next(iter(d["placements"].values())):
            placements = {
                did: ContinuousPlacement(
                    department_id=did,
                    x=p["x"], y=p["y"], width=p["width"], height=p["height"],
                    orientation_degrees=p.get("orientation_degrees", 0.0),
                )
                for did, p in d["placements"].items()
            }
            layout = ContinuousLayout(
                problem_id=problem.id,
                facility_width=problem.facility.width,
                facility_height=problem.facility.height,
                placements=placements,
            )
        else:
            raise ValueError(f"Unknown format in {path}")

        res = evaluate_canonical(problem, layout)
        canonical_results[name] = res
        print(f"\n--- {name} ({path}) ---")
        print(f"  Signature:              {res['layout_signature']}")
        print(f"  MHC ($):                ${res['material_handling_cost']:,.2f}")
        print(f"  Flow-Distance:          {res['flow_distance']:,.2f} m-moves")
        print(f"  Rel Raw Score:          {res['relationship_raw_score']:.2f}")
        print(f"  Rel Satisfaction (%):   {res['relationship_satisfaction_percentage']:.2f}%")
        print(f"  Hard Violations:        {res['hard_violations_count']}")
        print(f"  Soft Violations:        {res['soft_violations_count']}")
        print(f"  Soft Penalty ($):       ${res['soft_penalty']:,.2f}")
        for v in res["violations"]:
            print(f"    * Violation: {v['constraint_id']} ({v['classification']}): {v['message']}")

    # 3. Vibration Separation Constraint Detail Audit
    print("\n3. Soft Vibration Separation (CST_SOFT_VIBRATION_SEP) Geometric Audit:")
    for name, path in layouts_info:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        p_mach = d["placements"]["DEP_MACHINING"]
        p_qual = d["placements"]["DEP_QUALITY"]
        x_m = p_mach.get("x", p_mach.get("origin", {}).get("x"))
        y_m = p_mach.get("y", p_mach.get("origin", {}).get("y"))
        w_m = p_mach.get("width", p_mach.get("dimensions", {}).get("width"))
        h_m = p_mach.get("height", p_mach.get("dimensions", {}).get("height"))

        x_q = p_qual.get("x", p_qual.get("origin", {}).get("x"))
        y_q = p_qual.get("y", p_qual.get("origin", {}).get("y"))
        w_q = p_qual.get("width", p_qual.get("dimensions", {}).get("width"))
        h_q = p_qual.get("height", p_qual.get("dimensions", {}).get("height"))

        bb_m = ContinuousPlacement(department_id="DEP_MACHINING", x=x_m, y=y_m, width=w_m, height=h_m).bounding_box
        bb_q = ContinuousPlacement(department_id="DEP_QUALITY", x=x_q, y=y_q, width=w_q, height=h_q).bounding_box

        edge_dist = round(GeometryEngine.edge_to_edge_distance(bb_m, bb_q), 4)
        req_dist = 25.0
        deficit = max(0.0, round(req_dist - edge_dist, 4))
        penalty_rate = 2500.0
        penalty = round(deficit * penalty_rate, 2)

        print(f"  [{name:19s}] Distance: {edge_dist:6.2f}m | Req: {req_dist:5.2f}m | Deficit: {deficit:5.2f}m | Penalty: ${penalty:9,.2f}")

    # 4. Multi-Seed Ablation Study (5 Seeds across 4 Variants)
    print("\n4. Five-Seed Algorithmic Ablation Study (Seeds: 42, 101, 2024, 777, 999):")
    seeds = [42, 101, 2024, 777, 999]
    algo = GeneticLayoutAlgorithm()

    variants = {
        "A_Init_Only": {"generations": 0, "crossover_rate": 0.0, "mutation_rate": 0.0},
        "B_Mutation_Only": {"generations": 100, "crossover_rate": 0.0, "mutation_rate": 0.20},
        "C_Crossover_Only": {"generations": 100, "crossover_rate": 0.80, "mutation_rate": 0.00},
        "D_Full_GA": {"generations": 100, "crossover_rate": 0.80, "mutation_rate": 0.20},
    }

    ablation_5seed_data = {}
    for v_name, params in variants.items():
        records = []
        for s in seeds:
            cfg = GAConfig(
                population_size=40,
                generations=params["generations"],
                crossover_rate=params["crossover_rate"],
                mutation_rate=params["mutation_rate"],
                stagnation_limit=100,
                random_seed=s,
            )
            t0 = time.time()
            res = algo.solve_with_result(problem, config=cfg)
            elapsed = time.time() - t0

            # Count evaluations: pop_size + gen * (pop_size - elitism)
            evals = 40 if params["generations"] == 0 else 40 + (res.generation_count * 38)

            records.append({
                "seed": s,
                "best_mhc": res.best_mhc,
                "initial_mhc": res.initial_mhc,
                "runtime": round(elapsed, 3),
                "is_feasible": res.is_feasible,
                "evaluations": evals,
                "generations": res.generation_count,
            })

        mhc_list = [r["best_mhc"] for r in records]
        runtime_list = [r["runtime"] for r in records]
        eval_list = [r["evaluations"] for r in records]
        feasible_count = sum(1 for r in records if r["is_feasible"])

        summary = {
            "best_mhc": min(mhc_list),
            "mean_mhc": round(statistics.mean(mhc_list), 2),
            "median_mhc": round(statistics.median(mhc_list), 2),
            "worst_mhc": max(mhc_list),
            "std_dev_mhc": round(statistics.stdev(mhc_list), 2) if len(mhc_list) > 1 else 0.0,
            "mean_runtime": round(statistics.mean(runtime_list), 3),
            "mean_evaluations": round(statistics.mean(eval_list)),
            "feasible_rate_pct": (feasible_count / len(records)) * 100.0,
            "seed_records": records,
        }
        ablation_5seed_data[v_name] = summary

        print(
            f"  {v_name:17s} | Best: ${summary['best_mhc']:10,.2f} | Mean: ${summary['mean_mhc']:10,.2f} | "
            f"Median: ${summary['median_mhc']:10,.2f} | StdDev: ${summary['std_dev_mhc']:9,.2f} | "
            f"Time: {summary['mean_runtime']:5.2f}s | Evals: {summary['mean_evaluations']:4d} | Feasible: {summary['feasible_rate_pct']:.0f}%"
        )

    # 5. GA Seed 2024 Exact Reproduction Check
    print("\n5. GA Seed 2024 Exact Reproduction Check:")
    cfg_2024 = GAConfig(
        population_size=40,
        generations=100,
        crossover_rate=0.8,
        mutation_rate=0.2,
        stagnation_limit=100,
        random_seed=2024,
    )
    t0 = time.time()
    res_2024 = algo.solve_with_result(problem, config=cfg_2024)
    sig_new = generate_layout_signature(res_2024.best_layout)
    sig_saved = canonical_results["GA Best Solution"]["layout_signature"]

    print(f"  Saved GA Signature:  {sig_saved}")
    print(f"  Re-run GA Signature: {sig_new}")
    print(f"  Signatures Match:    {sig_saved == sig_new}")
    print(f"  Saved MHC:           ${canonical_results['GA Best Solution']['material_handling_cost']:,.2f}")
    print(f"  Re-run MHC:          ${res_2024.best_mhc:,.2f}")
    assert sig_saved == sig_new, "Signatures must be identical"
    assert abs(res_2024.best_mhc - 93876.54) < 0.01, f"Expected 93876.54, got {res_2024.best_mhc}"
    print("  CONFIRMED: Seed 2024 reproduces exactly $93,876.54 with bitwise identical signature!")

    # 6. Save full audit data
    audit_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "problem_hashes": prob_hashes,
        "canonical_results": canonical_results,
        "ablation_5seed": ablation_5seed_data,
        "seed_2024_reproduction": {
            "signature_match": sig_saved == sig_new,
            "signature": sig_new,
            "best_mhc": res_2024.best_mhc,
            "initial_mhc": res_2024.initial_mhc,
        },
    }

    out_path = os.path.join("data", "examples", "evaluation_audit_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print(f"\nSaved audit summary data to {out_path}")


if __name__ == "__main__":
    run_audit()
