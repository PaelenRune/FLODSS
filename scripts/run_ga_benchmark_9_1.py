"""Benchmark and validation runner for Phase 9.1: GA Verification & Reproducibility."""

import json
import math
import os
import statistics
import time
from typing import Any, Dict, List

from app.algorithms.ga.models import GAConfig, GAResult
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.algorithms.generator.models import GeneratorConfig
from app.algorithms.generator.search_guillotine_packing import GuillotineRowPackingEngine
from app.constraints.engine import ConstraintEngine
from app.evaluation.config import EvaluationConfig
from app.evaluation.engine import EvaluationEngine
from app.evaluation.evaluators import MaterialHandlingCostEvaluator
from app.models.constraint import ConstraintClassification
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.feasibility.service import RectangularFeasibilityService
from app.services.geometry_engine import GeometryEngine
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.services.problem_service import problem_service


def run_benchmark():
    problem = problem_service.get_example_problem("FLP_INDUSTRIAL_10")
    eval_engine = EvaluationEngine()
    mhc_evaluator = MaterialHandlingCostEvaluator()
    feasibility_service = RectangularFeasibilityService()
    validator = LayoutValidator()
    constraint_engine = ConstraintEngine()

    print("=================================================================")
    print("PHASE 9.1: GA VERIFICATION & REPRODUCIBLE BENCHMARK RUNNER")
    print("=================================================================\n")

    # 1. Standalone Guillotine Solution
    gen_cfg = GeneratorConfig()
    guillotine_res = GuillotineRowPackingEngine.search(problem, gen_cfg)
    assert guillotine_res.feasible, "Guillotine baseline must be feasible"
    guillotine_layout = guillotine_res.layout
    guillotine_eval = eval_engine.evaluate(problem, guillotine_layout)
    mhc_guillotine = round(guillotine_eval.objective_values["material_handling_cost"], 2)
    print(f"1. Standalone Guillotine MHC (A): ${mhc_guillotine:,.2f}")

    # Manual Baseline
    manual_path = os.path.join("data", "examples", "sample_layout.json")
    if os.path.exists(manual_path):
        with open(manual_path, "r", encoding="utf-8") as f:
            manual_layout = ContinuousLayout.model_validate(json.load(f))
        manual_eval = eval_engine.evaluate(problem, manual_layout)
        mhc_manual = round(manual_eval.objective_values["material_handling_cost"], 2)
        print(f"   Manual Baseline MHC:           ${mhc_manual:,.2f}\n")
    else:
        mhc_manual = 139498.75
        print(f"   Manual Baseline MHC (ref):     ${mhc_manual:,.2f}\n")

    # 2. 5-Seed Benchmark (pop=40, gen=100, cross=0.8, mut=0.2)
    seeds = [42, 101, 2024, 777, 999]
    algo = GeneticLayoutAlgorithm()

    benchmark_records = []
    best_overall_res: GAResult = None
    best_overall_seed = None

    print("--- 2. Five-Seed Benchmark (100 Generations, Stagnation=100) ---")
    for s in seeds:
        cfg = GAConfig(
            population_size=40,
            generations=100,
            crossover_rate=0.8,
            mutation_rate=0.2,
            stagnation_limit=100,
            random_seed=s,
        )
        t0 = time.time()
        res = algo.solve_with_result(problem, config=cfg)
        elapsed = time.time() - t0

        mhc_init = res.initial_mhc
        mhc_final = res.best_mhc
        init_adv = round(mhc_guillotine - mhc_init, 2)
        evo_adv = round(mhc_init - mhc_final, 2)
        tot_adv = round(mhc_guillotine - mhc_final, 2)
        init_share = (init_adv / tot_adv * 100.0) if tot_adv > 0 else 0.0
        evo_share = (evo_adv / tot_adv * 100.0) if tot_adv > 0 else 0.0

        rec = {
            "seed": s,
            "runtime_seconds": round(elapsed, 3),
            "generations": res.generation_count,
            "termination_reason": res.termination_reason.value,
            "is_feasible": res.is_feasible,
            "A_guillotine_mhc": mhc_guillotine,
            "B_init_mhc": mhc_init,
            "C_final_mhc": mhc_final,
            "D_init_adv": init_adv,
            "E_evo_adv": evo_adv,
            "F_total_adv": tot_adv,
            "init_share_pct": round(init_share, 1),
            "evo_share_pct": round(evo_share, 1),
            "signature": res.best_solution.metadata.get("layout_signature"),
            "soft_penalty": res.best_soft_penalty,
            "fitness": res.best_fitness,
        }
        benchmark_records.append(rec)
        print(
            f"Seed {s:4d} | MHC: ${mhc_final:10,.2f} | Init: ${mhc_init:10,.2f} | "
            f"Init Adv: ${init_adv:9,.2f} ({init_share:4.1f}%) | "
            f"Evo Adv: ${evo_adv:9,.2f} ({evo_share:4.1f}%) | "
            f"Time: {elapsed:5.2f}s | Gen: {res.generation_count:3d} | Feasible: {res.is_feasible}"
        )

        if best_overall_res is None or res.best_fitness < best_overall_res.best_fitness:
            best_overall_res = res
            best_overall_seed = s

    # 3. Also test with default stagnation_limit=30 (which was run in earlier phase)
    print("\n--- 2b. Five-Seed Benchmark (Default Stagnation=30, Max Gen=100) ---")
    stagnation_records = []
    for s in seeds:
        cfg = GAConfig(
            population_size=40,
            generations=100,
            crossover_rate=0.8,
            mutation_rate=0.2,
            stagnation_limit=30,
            random_seed=s,
        )
        t0 = time.time()
        res = algo.solve_with_result(problem, config=cfg)
        elapsed = time.time() - t0
        stagnation_records.append({
            "seed": s,
            "generations": res.generation_count,
            "best_mhc": res.best_mhc,
            "init_mhc": res.initial_mhc,
            "runtime": round(elapsed, 2),
            "termination": res.termination_reason.value,
        })
        print(
            f"Seed {s:4d} | MHC: ${res.best_mhc:10,.2f} | Gen: {res.generation_count:3d} | "
            f"Term: {res.termination_reason.value:25s} | Time: {elapsed:5.2f}s"
        )

    # 4. Statistical Summary (from 100-gen runs)
    mhc_values = [r["C_final_mhc"] for r in benchmark_records if r["is_feasible"]]
    best_mhc = min(mhc_values)
    worst_mhc = max(mhc_values)
    mean_mhc = round(statistics.mean(mhc_values), 2)
    median_mhc = round(statistics.median(mhc_values), 2)
    std_mhc = round(statistics.stdev(mhc_values), 2) if len(mhc_values) > 1 else 0.0
    distinct_sigs = len(set(r["signature"] for r in benchmark_records))
    feasible_rate = sum(1 for r in benchmark_records if r["is_feasible"]) / len(benchmark_records) * 100.0
    tot_runtime = round(sum(r["runtime_seconds"] for r in benchmark_records), 2)

    stats = {
        "best_mhc": best_mhc,
        "mean_mhc": mean_mhc,
        "median_mhc": median_mhc,
        "worst_mhc": worst_mhc,
        "sample_std_dev": std_mhc,
        "feasible_run_rate_pct": feasible_rate,
        "total_runtime_seconds": tot_runtime,
        "distinct_signatures": distinct_sigs,
    }

    print("\n--- 5-Seed Statistical Summary ---")
    for k, v in stats.items():
        print(f"  {k:25s}: {v}")

    # 5. Ablation Experiment on Seed 42
    print("\n--- 3. Ablation Experiment (Seed 42) ---")
    ablation_configs = {
        "A_Init_Only": GAConfig(population_size=40, generations=0, crossover_rate=0.0, mutation_rate=0.0, random_seed=42),
        "B_Mutation_Only": GAConfig(population_size=40, generations=100, crossover_rate=0.0, mutation_rate=0.2, stagnation_limit=100, random_seed=42),
        "C_Crossover_Only": GAConfig(population_size=40, generations=100, crossover_rate=0.8, mutation_rate=0.0, stagnation_limit=100, random_seed=42),
        "D_Full_GA": GAConfig(population_size=40, generations=100, crossover_rate=0.8, mutation_rate=0.2, stagnation_limit=100, random_seed=42),
    }

    ablation_results = {}
    for name, cfg in ablation_configs.items():
        t0 = time.time()
        res = algo.solve_with_result(problem, config=cfg)
        elapsed = time.time() - t0
        ablation_results[name] = {
            "best_mhc": res.best_mhc,
            "initial_mhc": res.initial_mhc,
            "improvement_mhc": round(res.initial_mhc - res.best_mhc, 2),
            "improvement_pct": round((res.initial_mhc - res.best_mhc) / res.initial_mhc * 100.0, 2) if res.initial_mhc > 0 else 0.0,
            "generations": res.generation_count,
            "runtime_seconds": round(elapsed, 3),
            "feasible": res.is_feasible,
        }
        print(
            f"{name:18s} | MHC: ${res.best_mhc:10,.2f} | Init: ${res.initial_mhc:10,.2f} | "
            f"Impr: ${ablation_results[name]['improvement_mhc']:9,.2f} ({ablation_results[name]['improvement_pct']:5.2f}%) | "
            f"Time: {elapsed:5.2f}s | Feasible: {res.is_feasible}"
        )

    # 6. Re-validation of Best Overall Layout
    print(f"\n--- 4. Strict Multi-Validator Audit of Best Layout (Seed {best_overall_seed}) ---")
    best_layout = best_overall_res.best_layout
    eval_rep = eval_engine.evaluate(problem, best_layout)

    # Validator 1: RectangularFeasibilityService
    rf_valid, rf_errors = feasibility_service.validate_rectangular_layout(problem, best_layout)
    print(f"Validator 1 (RectangularFeasibilityService): is_valid={rf_valid}, errors={len(rf_errors)}")
    for err in rf_errors:
        print(f"  ERR: {err}")

    # Validator 2: LayoutValidator
    lv_res = LayoutValidator.validate(problem, best_layout)
    print(f"Validator 2 (LayoutValidator): is_valid={lv_res.is_valid}, errors={len(lv_res.errors)}, overlap={lv_res.total_overlap_area} m2")

    # Validator 3: ConstraintEngine
    violations = constraint_engine.check_all(problem, best_layout)
    hard_violations = [v for v in violations if v.classification == ConstraintClassification.HARD]
    soft_violations = [v for v in violations if v.classification == ConstraintClassification.SOFT]
    print(f"Validator 3 (ConstraintEngine): hard_violations={len(hard_violations)}, soft_violations={len(soft_violations)}")

    # Specific seed 101 verification (reference comparison)
    print("\n--- 5. Comparison with Previous Reference MHC = $108,504.20 ---")
    res_101 = [r for r in benchmark_records if r["seed"] == 101][0]
    print(f"Seed 101 final MHC: ${res_101['C_final_mhc']:,.2f}")
    print(f"Best overall final MHC across 5 seeds: ${best_overall_res.best_mhc:,.2f} (Seed {best_overall_seed})")

    # 7. Persist Best Solution to data/examples/ga_optimized_industrial_10.json
    out_path = os.path.join("data", "examples", "ga_optimized_industrial_10.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    persisted_payload = {
        "problem_id": problem.id,
        "algorithm_name": "genetic_algorithm",
        "algorithm_version": "1.0.0",
        "random_seed": best_overall_seed,
        "config": {
            "population_size": 40,
            "generations": 100,
            "crossover_rate": 0.8,
            "mutation_rate": 0.2,
            "stagnation_limit": 100,
        },
        "chromosome": best_overall_res.best_chromosome.model_dump(),
        "layout_signature": eval_rep.layout_signature,
        "is_feasible": best_overall_res.is_feasible,
        "placements": {
            did: {
                "department_id": did,
                "x": round(cp.x, 4),
                "y": round(cp.y, 4),
                "width": round(cp.width, 4),
                "height": round(cp.height, 4),
                "area": round(cp.width * cp.height, 4),
                "aspect_ratio": round(max(cp.width, cp.height) / min(cp.width, cp.height), 4),
            }
            for did, cp in best_layout.placements.items()
        },
        "evaluation": {
            "material_handling_cost": round(eval_rep.objective_values.get("material_handling_cost", 0.0), 2),
            "flow_distance": round(eval_rep.objective_values.get("total_flow_distance", 0.0), 2),
            "relationship_score": round(eval_rep.objective_values.get("relationship_satisfaction", 0.0), 2),
            "hard_violations": len(hard_violations),
            "soft_penalty": round(best_overall_res.best_soft_penalty, 2),
            "combined_fitness": round(best_overall_res.best_fitness, 2),
            "initial_mhc": round(best_overall_res.initial_mhc, 2),
            "improvement_mhc": round(best_overall_res.initial_mhc - best_overall_res.best_mhc, 2),
            "improvement_percentage": round((best_overall_res.initial_mhc - best_overall_res.best_mhc) / best_overall_res.initial_mhc * 100.0, 2),
        },
        "validation": {
            "rectangular_feasibility_valid": rf_valid,
            "layout_validator_valid": lv_res.is_valid,
            "constraint_engine_hard_violations": len(hard_violations),
            "zero_overlap": lv_res.total_overlap_area == 0.0,
            "department_count": len(best_layout.placements),
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(persisted_payload, f, indent=2)
    print(f"\nPersisted best layout to {out_path} (MHC: ${persisted_payload['evaluation']['material_handling_cost']:,.2f})")

    # Output JSON summary for artifact / report writing
    summary = {
        "standalone_guillotine_mhc": mhc_guillotine,
        "manual_baseline_mhc": mhc_manual,
        "benchmark_records": benchmark_records,
        "stagnation_records": stagnation_records,
        "statistics": stats,
        "ablation_results": ablation_results,
        "reported_seed_101_mhc": res_101["C_final_mhc"],
        "best_overall_seed": best_overall_seed,
        "best_overall_mhc": best_overall_res.best_mhc,
    }

    summary_path = os.path.join("data", "examples", "ga_benchmark_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary data saved to {summary_path}")


if __name__ == "__main__":
    run_benchmark()
