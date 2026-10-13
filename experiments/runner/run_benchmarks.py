"""CLI and module runner for executing reproducible facility layout benchmarks."""

import json
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.benchmark.models import BenchmarkConfig
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.exporter import (
    export_aldep_candidates_csv,
    export_benchmark_json,
    export_comparison_csv,
    export_craft_runs_csv,
)


def run_benchmark_experiments() -> None:
    """Run full benchmark suite and export all experimental results to disk."""
    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / "configs" / "benchmark_config.json"
    results_dir = root_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_dict = json.load(f)
        config = BenchmarkConfig.model_validate(cfg_dict)
    else:
        config = BenchmarkConfig()

    print(f"[*] Starting BenchmarkRunner with {len(config.problem_ids)} problems and {len(config.aldep_seeds)} seeds...")
    runner = BenchmarkRunner(config=config)
    result = runner.run_all()

    # Export artifacts
    json_path = results_dir / "benchmark_summary.json"
    csv_comp_path = results_dir / "benchmark_summary.csv"
    csv_aldep_path = results_dir / "aldep_candidates.csv"
    csv_craft_path = results_dir / "craft_runs.csv"

    export_benchmark_json(result, json_path)
    export_comparison_csv(result.comparison_table, csv_comp_path)
    export_aldep_candidates_csv(result.aldep_candidates, csv_aldep_path)
    export_craft_runs_csv(result.craft_records, csv_craft_path)

    print(f"[OK] Benchmark run complete! Run ID: {result.run_id}")
    print(f"    - JSON summary: {json_path}")
    print(f"    - Comparison CSV: {csv_comp_path}")
    print(f"    - ALDEP candidates CSV: {csv_aldep_path} ({len(result.aldep_candidates)} rows)")
    print(f"    - CRAFT runs CSV: {csv_craft_path} ({len(result.craft_records)} rows)")


if __name__ == "__main__":
    run_benchmark_experiments()
