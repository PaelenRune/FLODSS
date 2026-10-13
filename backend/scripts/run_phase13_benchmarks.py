"""Phase 13 Multi-Seed Industrial Benchmark Runner.

Executes and measures:
- FeasibleLayoutGenerator (Constructive Guillotine Row Packing)
- GeneticLayoutAlgorithm (Fixed GA: population=20, generations=20)
- Adaptive Strategy Engine (Heuristic selector + pipeline + validation + fallback)
- CORELAP & ALDEP (where applicable)

Metrics measured:
- Runtime (ms)
- Peak memory (tracemalloc, KB)
- Actual fitness evaluations / algorithm calls
- Feasibility success rate (100% hard constraints satisfied)
- Canonical metrics via CanonicalEvaluationService: MHC ($), REL (%), Soft Penalty ($)
- Provenance hashes and signatures
"""

import json
import logging
from pathlib import Path
import time
import tracemalloc
from typing import Any, Dict, List

from app.algorithms.ga import GAConfig, GeneticLayoutAlgorithm
from app.algorithms.generator import GeneratorConfig, GeneratorStrategy, FeasibleLayoutGenerator
from app.evaluation.canonical import CanonicalEvaluationService
from app.models.representation import ContinuousLayout
from app.optimization.adaptive import AdaptiveConfig, StrategyExecutionEngine
from app.services.layout_normalizer import generate_layout_signature
from app.services.problem_service import problem_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase13Benchmarks")

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"
BENCHMARK_PROBLEMS = [
    ("FLP_INDUSTRIAL_10", DATA_DIR / "sample_plant.json"),
    ("HIGH_DENSITY_15", DATA_DIR / "synthetic_high_density_15.json"),
    ("HIGH_DENSITY_20", DATA_DIR / "synthetic_high_density_20.json"),
    ("CONSTRAINED_FACTORY_12", DATA_DIR / "synthetic_constrained_factory_12.json"),
    ("LOGISTICS_FACTORY_15", DATA_DIR / "synthetic_logistics_factory_15.json"),
]

SEEDS = [42, 101, 202, 303, 404]


def run_benchmarks():
    results: List[Dict[str, Any]] = []

    for prob_id, prob_file in BENCHMARK_PROBLEMS:
        if not prob_file.exists():
            logger.warning(f"File {prob_file} does not exist, skipping.")
            continue

        problem = problem_service.load_problem(prob_file)
        logger.info(f"--- Running Benchmarks for {prob_id} ({len(problem.departments)} depts) ---")

        for seed in SEEDS:
            # 1. FeasibleLayoutGenerator (Constructive Guillotine)
            tracemalloc.start()
            t0 = time.perf_counter()
            gen_cfg = GeneratorConfig(
                strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING,
                random_seed=seed,
                time_budget_seconds=10.0,
            )
            gen = FeasibleLayoutGenerator()
            gen_res = gen.generate(problem, config=gen_cfg)
            t1 = time.perf_counter()
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            runtime_ms = (t1 - t0) * 1000.0
            peak_kb = peak_mem / 1024.0

            if gen_res.feasible and gen_res.layout:
                report = CanonicalEvaluationService.evaluate(problem, gen_res.layout)
                sig = generate_layout_signature(gen_res.layout)
                results.append({
                    "problem_id": prob_id,
                    "algorithm": "FeasibleGenerator_Guillotine",
                    "seed": seed,
                    "runtime_ms": round(runtime_ms, 2),
                    "peak_memory_kb": round(peak_kb, 2),
                    "algorithm_calls": 1,
                    "evaluations_count": 1,
                    "is_feasible": report.is_feasible,
                    "is_complete": report.is_complete,
                    "mhc": round(report.material_handling_cost, 2),
                    "rel_pct": round(report.relationship_satisfaction_percentage, 2),
                    "soft_penalty": round(report.soft_penalty, 2),
                    "layout_signature": sig,
                })
            else:
                results.append({
                    "problem_id": prob_id,
                    "algorithm": "FeasibleGenerator_Guillotine",
                    "seed": seed,
                    "runtime_ms": round(runtime_ms, 2),
                    "peak_memory_kb": round(peak_kb, 2),
                    "algorithm_calls": 1,
                    "evaluations_count": 1,
                    "is_feasible": False,
                    "is_complete": False,
                    "mhc": None,
                    "rel_pct": None,
                    "soft_penalty": None,
                    "layout_signature": None,
                })

            # 2. Fixed GA (population=20, generations=20)
            tracemalloc.start()
            t0 = time.perf_counter()
            ga_cfg = GAConfig(
                population_size=20,
                max_generations=20,
                random_seed=seed,
                time_budget_seconds=10.0,
            )
            ga = GeneticLayoutAlgorithm()
            try:
                ga_res = ga.solve_with_result(problem, config=ga_cfg)
                t1 = time.perf_counter()
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                runtime_ms = (t1 - t0) * 1000.0
                peak_kb = peak_mem / 1024.0

                actual_evals = (ga_res.generation_count + 1) * ga_cfg.population_size

                if ga_res and ga_res.best_layout:
                    report = CanonicalEvaluationService.evaluate(problem, ga_res.best_layout)
                    sig = generate_layout_signature(ga_res.best_layout)
                    results.append({
                        "problem_id": prob_id,
                        "algorithm": "Fixed_GA_v1",
                        "seed": seed,
                        "runtime_ms": round(runtime_ms, 2),
                        "peak_memory_kb": round(peak_kb, 2),
                        "algorithm_calls": 1,
                        "evaluations_count": actual_evals,
                        "is_feasible": report.is_feasible,
                        "is_complete": report.is_complete,
                        "mhc": round(report.material_handling_cost, 2),
                        "rel_pct": round(report.relationship_satisfaction_percentage, 2),
                        "soft_penalty": round(report.soft_penalty, 2),
                        "layout_signature": sig,
                    })
                else:
                    results.append({
                        "problem_id": prob_id,
                        "algorithm": "Fixed_GA_v1",
                        "seed": seed,
                        "runtime_ms": round(runtime_ms, 2),
                        "peak_memory_kb": round(peak_kb, 2),
                        "algorithm_calls": 1,
                        "evaluations_count": actual_evals,
                        "is_feasible": False,
                        "is_complete": False,
                        "mhc": None,
                        "rel_pct": None,
                        "soft_penalty": None,
                        "layout_signature": None,
                    })
            except Exception as e:
                tracemalloc.stop()
                logger.warning(f"Fixed GA failed on {prob_id} seed {seed}: {e}")
                results.append({
                    "problem_id": prob_id,
                    "algorithm": "Fixed_GA_v1",
                    "seed": seed,
                    "runtime_ms": 0.0,
                    "peak_memory_kb": 0.0,
                    "algorithm_calls": 1,
                    "evaluations_count": 0,
                    "is_feasible": False,
                    "is_complete": False,
                    "mhc": None,
                    "rel_pct": None,
                    "soft_penalty": None,
                    "layout_signature": None,
                    "error": str(e),
                })

            # 3. Adaptive Strategy Engine
            tracemalloc.start()
            t0 = time.perf_counter()
            ad_cfg = AdaptiveConfig(
                random_seed=seed,
                time_limit_seconds=10.0,
                allow_ga=True,
                ga_population_size=20,
                ga_generations=20,
            )
            ad_res = StrategyExecutionEngine.execute(problem=problem, config=ad_cfg)
            t1 = time.perf_counter()
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            runtime_ms = (t1 - t0) * 1000.0
            peak_kb = peak_mem / 1024.0

            rec = ad_res.final_recommendation or {}
            results.append({
                "problem_id": prob_id,
                "algorithm": f"Adaptive_{ad_res.selected_strategy.name.replace(' ', '_')}",
                "seed": seed,
                "runtime_ms": round(runtime_ms, 2),
                "peak_memory_kb": round(peak_kb, 2),
                "algorithm_calls": ad_res.total_algorithm_calls,
                "evaluations_count": len(ad_res.candidate_portfolio.items),
                "is_feasible": ad_res.feasible_status,
                "is_complete": ad_res.candidate_portfolio.feasible_candidates_count > 0,
                "mhc": round(float(rec.get("material_handling_cost", 0.0)), 2) if rec.get("material_handling_cost") else None,
                "rel_pct": round(float(rec.get("relationship_satisfaction", 0.0)), 2) if rec.get("relationship_satisfaction") else None,
                "soft_penalty": round(float(rec.get("soft_penalty", 0.0)), 2) if rec.get("soft_penalty") is not None else None,
                "layout_signature": rec.get("layout_signature"),
                "termination_reason": ad_res.termination_reason,
            })

    out_file = DATA_DIR / "phase13_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved {len(results)} benchmark execution records to {out_file}")


if __name__ == "__main__":
    run_benchmarks()
