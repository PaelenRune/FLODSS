"""Unit and integration test suite for Phase 7.1: Benchmark & Algorithm Comparison."""

import csv
import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.benchmark.models import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkComparisonRow,
    ALDEPCandidateRecord,
    ALDEPProblemSummary,
    CORELAPRunRecord,
    CRAFTRunRecord,
)
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.exporter import (
    export_benchmark_json,
    export_comparison_csv,
    export_aldep_candidates_csv,
    export_craft_runs_csv,
)
from app.evaluation.config import EvaluationConfig
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.models.problem import FacilityLayoutProblem
from app.services.problem_service import problem_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mini_benchmark_config() -> BenchmarkConfig:
    """Fast, lightweight configuration for testing benchmark execution mechanics."""
    return BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4"],
        aldep_seeds=[42, 101],
        aldep_candidates_per_seed=3,
        aldep_cell_size=10.0,
        aldep_strip_width_cells=1,
        craft_max_iterations=10,
    )


# ---------------------------------------------------------------------------
# 1. Deterministic Benchmark Reproduction
# ---------------------------------------------------------------------------
def test_01_deterministic_benchmark_reproduction(mini_benchmark_config: BenchmarkConfig):
    """Test 1: Running the benchmark twice with identical config yields identical metrics."""
    runner1 = BenchmarkRunner(config=mini_benchmark_config)
    res1 = runner1.run_all(run_id="test_run_1")

    runner2 = BenchmarkRunner(config=mini_benchmark_config)
    res2 = runner2.run_all(run_id="test_run_2")

    # Verify ALDEP summary repeatability
    s1 = res1.aldep_summaries["FLP_ACADEMIC_4"]
    s2 = res2.aldep_summaries["FLP_ACADEMIC_4"]
    assert s1.total_trials == s2.total_trials == 6
    assert s1.best_mhc == s2.best_mhc
    assert s1.median_mhc == s2.median_mhc
    assert s1.std_mhc == s2.std_mhc

    # Verify CORELAP repeatability
    cr1 = next(r for r in res1.corelap_records if r.problem_id == "FLP_ACADEMIC_4")
    cr2 = next(r for r in res2.corelap_records if r.problem_id == "FLP_ACADEMIC_4")
    assert cr1.mhc == cr2.mhc
    assert cr1.layout_signature == cr2.layout_signature


# ---------------------------------------------------------------------------
# 2. ALDEP Seed Repeatability
# ---------------------------------------------------------------------------
def test_02_aldep_seed_repeatability():
    """Test 2: Specific seeds generate identical candidate signatures in benchmark."""
    cfg = BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4"],
        aldep_seeds=[42],
        aldep_candidates_per_seed=5,
        aldep_cell_size=10.0,
        aldep_strip_width_cells=1,
    )
    runner = BenchmarkRunner(config=cfg)
    res = runner.run_all()
    cands = res.aldep_candidates

    # Run again with same seed
    res2 = runner.run_all()
    cands2 = res2.aldep_candidates

    assert len(cands) == len(cands2) == 5
    for c1, c2 in zip(cands, cands2):
        assert c1.candidate_id == c2.candidate_id
        assert c1.layout_signature == c2.layout_signature
        assert c1.mhc == c2.mhc


# ---------------------------------------------------------------------------
# 3. Incomplete Result Exclusion
# ---------------------------------------------------------------------------
def test_03_incomplete_result_exclusion():
    """Test 3: Incomplete solutions (e.g. CORELAP on FLP_INDUSTRIAL_10) have mhc=None and are excluded."""
    cfg = BenchmarkConfig(
        problem_ids=["FLP_INDUSTRIAL_10"],
        aldep_seeds=[42],
        aldep_candidates_per_seed=1,
    )
    runner = BenchmarkRunner(config=cfg)
    res = runner.run_all()

    corelap_rec = next(r for r in res.corelap_records if r.problem_id == "FLP_INDUSTRIAL_10")
    assert corelap_rec.completion is False
    assert corelap_rec.feasibility is False
    assert corelap_rec.mhc is None

    # Check comparison table row
    comp_row = next(r for r in res.comparison_table if r.algorithm == "CORELAP" and r.problem_id == "FLP_INDUSTRIAL_10")
    assert comp_row.complete is False
    assert comp_row.feasible is False
    assert comp_row.mhc is None
    assert "INCOMPLETE" in comp_row.notes


# ---------------------------------------------------------------------------
# 4. CRAFT Initial Layout Validation
# ---------------------------------------------------------------------------
def test_04_craft_initial_layout_validation():
    """Test 4: CRAFT rejects incomplete or geometrically invalid initial layouts."""
    runner = BenchmarkRunner()
    problem = problem_service.get_example_problem("FLP_ACADEMIC_4")

    # Incomplete layout (missing DEP_D)
    invalid_layout = ContinuousLayout(
        problem_id="FLP_ACADEMIC_4",
        facility_width=120.0,
        facility_height=120.0,
        placements={
            "DEP_A": ContinuousPlacement(department_id="DEP_A", x=0, y=0, width=10, height=10),
            "DEP_B": ContinuousPlacement(department_id="DEP_B", x=10, y=0, width=10, height=10),
            "DEP_C": ContinuousPlacement(department_id="DEP_C", x=20, y=0, width=10, height=10),
        },
    )

    craft_rec = runner._run_craft(problem, invalid_layout, "Invalid Initial")
    assert craft_rec is None, "CRAFT must not run on invalid/incomplete layouts!"


# ---------------------------------------------------------------------------
# 5. Same Evaluation Config Enforcement
# ---------------------------------------------------------------------------
def test_05_same_evaluation_config_enforcement():
    """Test 5: Unified EvaluationConfig is enforced across all algorithms."""
    custom_eval = EvaluationConfig(
        default_cost_per_unit_distance=2.5,
    )
    cfg = BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4"],
        aldep_seeds=[42],
        aldep_candidates_per_seed=2,
        evaluation_config=custom_eval,
    )
    runner = BenchmarkRunner(config=cfg)
    assert runner.eval_engine.config.default_cost_per_unit_distance == 2.5
    res = runner.run_all()
    assert res.config.evaluation_config.default_cost_per_unit_distance == 2.5


# ---------------------------------------------------------------------------
# 6. Duplicate Signature Handling
# ---------------------------------------------------------------------------
def test_06_duplicate_signature_handling():
    """Test 6: Duplicate layout signatures are detected and tracked across candidates."""
    # When generating many candidates with identical seeds or deterministic steps
    cfg = BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4"],
        aldep_seeds=[42, 42],  # Duplicate seeds intentionally
        aldep_candidates_per_seed=3,
        aldep_cell_size=10.0,
        aldep_strip_width_cells=1,
    )
    runner = BenchmarkRunner(config=cfg)
    res = runner.run_all()

    s = res.aldep_summaries["FLP_ACADEMIC_4"]
    assert s.duplicate_count >= 3
    assert s.unique_layout_count <= 3

    dup_candidates = [c for c in res.aldep_candidates if c.is_duplicate]
    assert len(dup_candidates) >= 3
    for dc in dup_candidates:
        assert dc.duplicate_of_id is not None


# ---------------------------------------------------------------------------
# 7. Correct Success Rate Calculation
# ---------------------------------------------------------------------------
def test_07_correct_success_rate_calculation():
    """Test 7: Completion rate and feasibility rate are computed separately."""
    cfg = BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4", "FLP_INDUSTRIAL_10"],
        aldep_seeds=[42],
        aldep_candidates_per_seed=5,
    )
    runner = BenchmarkRunner(config=cfg)
    res = runner.run_all()

    # Academic 4: 100% complete, 100% feasible
    s4 = res.aldep_summaries["FLP_ACADEMIC_4"]
    assert s4.completion_rate == 1.0
    assert s4.feasibility_rate == 1.0

    # Industrial 10: 100% complete on grid, 0% feasible in continuous bounding box space
    s10 = res.aldep_summaries["FLP_INDUSTRIAL_10"]
    assert s10.completion_rate == 1.0
    assert s10.feasibility_rate == 0.0


# ---------------------------------------------------------------------------
# 8. Median and Standard Deviation Correctness
# ---------------------------------------------------------------------------
def test_08_median_and_standard_deviation_correctness():
    """Test 8: Median and standard deviation match numpy calculations over the feasible sample."""
    cfg = BenchmarkConfig(
        problem_ids=["FLP_ACADEMIC_4"],
        aldep_seeds=[42, 101, 2024],
        aldep_candidates_per_seed=5,
        aldep_cell_size=10.0,
        aldep_strip_width_cells=1,
    )
    runner = BenchmarkRunner(config=cfg)
    res = runner.run_all()

    s = res.aldep_summaries["FLP_ACADEMIC_4"]
    feasible_mhcs = [c.mhc for c in res.aldep_candidates if c.geometric_feasibility and c.mhc is not None]

    assert len(feasible_mhcs) == s.sample_size_mhc
    assert s.median_mhc == pytest.approx(float(np.median(feasible_mhcs)), rel=1e-4)
    assert s.std_mhc == pytest.approx(float(np.std(feasible_mhcs)), rel=1e-4)
    assert s.best_mhc == pytest.approx(float(np.min(feasible_mhcs)), rel=1e-4)
    assert s.worst_mhc == pytest.approx(float(np.max(feasible_mhcs)), rel=1e-4)


# ---------------------------------------------------------------------------
# 9. JSON and CSV Export
# ---------------------------------------------------------------------------
def test_09_json_and_csv_export(tmp_path: Path, mini_benchmark_config: BenchmarkConfig):
    """Test 9: JSON and CSV export create valid, populated disk files."""
    runner = BenchmarkRunner(config=mini_benchmark_config)
    res = runner.run_all(run_id="test_export")

    json_file = tmp_path / "benchmark_summary.json"
    comp_csv = tmp_path / "benchmark_summary.csv"
    aldep_csv = tmp_path / "aldep_candidates.csv"
    craft_csv = tmp_path / "craft_runs.csv"

    export_benchmark_json(res, json_file)
    export_comparison_csv(res.comparison_table, comp_csv)
    export_aldep_candidates_csv(res.aldep_candidates, aldep_csv)
    export_craft_runs_csv(res.craft_records, craft_csv)

    # Verify JSON
    assert json_file.exists()
    with open(json_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["run_id"] == "test_export"
    assert len(loaded["comparison_table"]) == len(res.comparison_table)

    # Verify CSV files
    assert comp_csv.exists()
    with open(comp_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == len(res.comparison_table) + 1  # Header + rows

    assert aldep_csv.exists()
    with open(aldep_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == len(res.aldep_candidates) + 1

    assert craft_csv.exists()
    with open(craft_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == len(res.craft_records) + 1


# ---------------------------------------------------------------------------
# 10. Benchmark Report Schema
# ---------------------------------------------------------------------------
def test_10_benchmark_report_schema(mini_benchmark_config: BenchmarkConfig):
    """Test 10: BenchmarkResult satisfies all required fields and models."""
    runner = BenchmarkRunner(config=mini_benchmark_config)
    res = runner.run_all()

    assert isinstance(res, BenchmarkResult)
    assert res.run_id.startswith("bench_")
    assert res.timestamp is not None
    assert len(res.comparison_table) > 0
    assert "FLP_ACADEMIC_4" in res.aldep_summaries
    assert len(res.corelap_records) > 0
    assert len(res.craft_records) > 0


# ---------------------------------------------------------------------------
# 11. API Integration Tests
# ---------------------------------------------------------------------------
def test_11_api_benchmarks_run_endpoint(client: TestClient):
    """Test 11: POST /api/benchmarks/run executes benchmark and returns 200."""
    payload = {
        "config": {
            "problem_ids": ["FLP_ACADEMIC_4"],
            "aldep_seeds": [42],
            "aldep_candidates_per_seed": 2,
        }
    }
    resp = client.post("/api/benchmarks/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert "comparison_table" in data
    assert "aldep_summaries" in data
    assert len(data["comparison_table"]) > 0

    run_id = data["run_id"]

    # Test GET /api/benchmarks/results/{run_id}
    resp_get = client.get(f"/api/benchmarks/results/{run_id}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["run_id"] == run_id

    # Test GET /api/benchmarks/latest
    resp_latest = client.get("/api/benchmarks/latest")
    assert resp_latest.status_code == 200
    data_latest = resp_latest.json()
    assert data_latest["run_id"] == run_id


# ---------------------------------------------------------------------------
# 12. Frontend Production Build Artifacts Verification
# ---------------------------------------------------------------------------
def test_12_frontend_production_build_artifacts():
    """Test 12: Verify frontend production bundle HTML exists and is populated."""
    dist_html = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "index.html"
    assert dist_html.exists(), f"Frontend production build HTML not found at {dist_html}"
    assert dist_html.stat().st_size > 100, "Frontend production HTML must not be empty"
