"""Export utilities for benchmark results in JSON and CSV formats."""

import csv
import json
from pathlib import Path
from typing import List, Union

from app.benchmark.models import (
    ALDEPCandidateRecord,
    BenchmarkComparisonRow,
    BenchmarkResult,
    CRAFTRunRecord,
)


def export_benchmark_json(result: BenchmarkResult, output_path: Union[str, Path]) -> Path:
    """Save full BenchmarkResult to formatted JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    return path


def export_comparison_csv(
    comparison_table: List[BenchmarkComparisonRow],
    output_path: Union[str, Path],
) -> Path:
    """Export comparison table to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "algorithm",
        "problem_id",
        "run_or_seed",
        "complete",
        "feasible",
        "mhc",
        "flow_distance",
        "relationship_satisfaction",
        "constraint_violations",
        "runtime_seconds",
        "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in comparison_table:
            row_dict = row.model_dump()
            writer.writerow({k: ("" if row_dict.get(k) is None else row_dict.get(k)) for k in fields})
    return path


def export_aldep_candidates_csv(
    candidates: List[ALDEPCandidateRecord],
    output_path: Union[str, Path],
) -> Path:
    """Export detailed candidate-level ALDEP logs to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "problem_id",
        "seed",
        "candidate_id",
        "candidate_index",
        "completion_status",
        "placed_department_count",
        "total_department_count",
        "geometric_feasibility",
        "hard_constraint_violations",
        "layout_signature",
        "is_duplicate",
        "duplicate_of_id",
        "mhc",
        "flow_distance",
        "relationship_satisfaction",
        "execution_time_seconds",
        "failure_reason",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for cand in candidates:
            c_dict = cand.model_dump()
            writer.writerow({k: ("" if c_dict.get(k) is None else c_dict.get(k)) for k in fields})
    return path


def export_craft_runs_csv(
    craft_records: List[CRAFTRunRecord],
    output_path: Union[str, Path],
) -> Path:
    """Export CRAFT improvement heuristic run records to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "problem_id",
        "initial_source",
        "initial_mhc",
        "final_mhc",
        "absolute_improvement",
        "percentage_improvement",
        "accepted_swaps",
        "termination_reason",
        "initial_layout_signature",
        "final_layout_signature",
        "runtime_seconds",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for cr in craft_records:
            cr_dict = cr.model_dump()
            writer.writerow({k: ("" if cr_dict.get(k) is None else cr_dict.get(k)) for k in fields})
    return path
