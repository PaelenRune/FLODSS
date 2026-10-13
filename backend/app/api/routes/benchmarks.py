"""API routes for running and querying benchmark experiments."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_job_slot
from app.benchmark.models import BenchmarkConfig, BenchmarkResult
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.exporter import (
    export_aldep_candidates_csv,
    export_benchmark_json,
    export_comparison_csv,
    export_craft_runs_csv,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# In-memory storage for benchmark execution runs
_benchmark_cache: Dict[str, BenchmarkResult] = {}
_latest_run_id: Optional[str] = None


class BenchmarkRunRequest(BaseModel):
    """Payload to trigger benchmark run with optional configuration overrides."""

    config: Optional[BenchmarkConfig] = None


@router.post("/run", response_model=BenchmarkResult)
def run_benchmark(
    payload: Optional[BenchmarkRunRequest] = None,
    _slot: Any = Depends(get_job_slot),
) -> BenchmarkResult:
    """Execute synchronous benchmark across CORELAP, ALDEP, and CRAFT."""
    global _latest_run_id
    cfg = payload.config if payload and payload.config else BenchmarkConfig()
    runner = BenchmarkRunner(config=cfg)
    result = runner.run_all()

    # Cache run in memory
    _benchmark_cache[result.run_id] = result
    _latest_run_id = result.run_id

    # Persist latest results to disk
    results_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "experiments" / "results"
    try:
        results_dir.mkdir(parents=True, exist_ok=True)
        export_benchmark_json(result, results_dir / "benchmark_summary.json")
        export_comparison_csv(result.comparison_table, results_dir / "benchmark_summary.csv")
        export_aldep_candidates_csv(result.aldep_candidates, results_dir / "aldep_candidates.csv")
        export_craft_runs_csv(result.craft_records, results_dir / "craft_runs.csv")
    except Exception:
        # Non-critical if disk write encounters filesystem restrictions
        pass

    return result


@router.get("/latest", response_model=BenchmarkResult)
def get_latest_benchmark_result() -> BenchmarkResult:
    """Retrieve the most recent benchmark run result."""
    global _latest_run_id
    if _latest_run_id and _latest_run_id in _benchmark_cache:
        return _benchmark_cache[_latest_run_id]

    # Try loading from disk if cache is empty
    results_json = Path(__file__).resolve().parent.parent.parent.parent.parent / "experiments" / "results" / "benchmark_summary.json"
    if results_json.exists():
        try:
            with open(results_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_result = BenchmarkResult.model_validate(data)
            _benchmark_cache[cached_result.run_id] = cached_result
            _latest_run_id = cached_result.run_id
            return cached_result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read persisted benchmark: {str(e)}")

    raise HTTPException(status_code=404, detail="No benchmark runs have been recorded yet.")


@router.get("/results/{run_id}", response_model=BenchmarkResult)
def get_benchmark_result(run_id: str) -> BenchmarkResult:
    """Retrieve a specific benchmark result by its run_id."""
    if run_id in _benchmark_cache:
        return _benchmark_cache[run_id]

    # Try loading from disk if run_id matches persisted file
    results_json = Path(__file__).resolve().parent.parent.parent.parent.parent / "experiments" / "results" / "benchmark_summary.json"
    if results_json.exists():
        try:
            with open(results_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("run_id") == run_id:
                cached_result = BenchmarkResult.model_validate(data)
                _benchmark_cache[cached_result.run_id] = cached_result
                return cached_result
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Benchmark run '{run_id}' not found.")
