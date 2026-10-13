"""Comprehensive verification test suite for Phase 8.1: Generated Layout Verification & Improvement Baseline."""

import json
from pathlib import Path
import pytest
from unittest.mock import patch

from app.models.geometry import Point2D, Dimensions2D, BoundingBox
from app.models.problem import FacilityLayoutProblem
from app.models.constraint import ConstraintClassification
from app.models.representation import ContinuousLayout
from app.algorithms.generator.models import GeneratorConfig, GeneratorStrategy, GeneratorTerminationReason
from app.algorithms.generator.solver import FeasibleLayoutGenerator
from app.algorithms.craft.solver import CRAFTAlgorithm
from app.algorithms.craft.models import CRAFTTerminationReason
from app.evaluation.engine import EvaluationEngine
from app.evaluation.config import EvaluationConfig
from app.services.problem_service import problem_service
from app.services.layout_validator import LayoutValidator
from app.services.layout_normalizer import generate_layout_signature


EXPECTED_SIGNATURE = "61c4bf88996517780fd1f43839d1e1654c6be9276072a9799c4a7e1c8fc12174"
SAVED_LAYOUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "generated_industrial_10.json"
BASELINE_LAYOUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_layout.json"


@pytest.fixture
def industrial_10_problem() -> FacilityLayoutProblem:
    return problem_service.get_example_problem("FLP_INDUSTRIAL_10")


@pytest.fixture
def generator_config() -> GeneratorConfig:
    return GeneratorConfig(strategy=GeneratorStrategy.GUILLOTINE_ROW_PACKING)


# ---------------------------------------------------------------------------
# 1. Generator Deterministic Repeatability (10 Runs)
# ---------------------------------------------------------------------------

def test_01_generator_deterministic_repeatability_10_runs(
    industrial_10_problem: FacilityLayoutProblem,
    generator_config: GeneratorConfig,
):
    """Running FeasibleLayoutGenerator 10 times yields bitwise identical 10/10 feasible layouts."""
    solver = FeasibleLayoutGenerator()
    observed_signatures = []

    for run_idx in range(10):
        _, result = solver.solve_with_result(industrial_10_problem, config=generator_config)

        # 1. Completeness
        assert result.success is True, f"Run {run_idx + 1} failed"
        assert result.complete is True
        assert result.placed_department_count == 10
        assert result.total_department_count == 10
        assert result.termination_reason == GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND

        # 2. Geometric validation
        layout = result.layout
        assert layout is not None
        val = LayoutValidator.validate(industrial_10_problem, layout)
        assert val.is_valid is True
        assert val.total_overlap_area == 0.0
        assert len(val.errors) == 0

        # 3. Signature consistency
        sig = result.layout_signature or generate_layout_signature(layout)
        assert sig == EXPECTED_SIGNATURE, f"Run {run_idx + 1} signature divergence: {sig}"
        observed_signatures.append(sig)

    assert len(set(observed_signatures)) == 1, "Expected exactly 1 deterministic signature across 10 runs"


# ---------------------------------------------------------------------------
# 2. Baseline Independence
# ---------------------------------------------------------------------------

def test_02_generator_baseline_independence(
    industrial_10_problem: FacilityLayoutProblem,
    generator_config: GeneratorConfig,
):
    """The generator executes successfully and produces the identical solution even without baseline files."""
    solver = FeasibleLayoutGenerator()

    # Verify that the generator source code contains zero references to sample_layout
    import app.algorithms.generator.search_guillotine_packing as gp
    import app.algorithms.generator.solver as gsol
    with open(gp.__file__, "r", encoding="utf-8") as f:
        assert "sample_layout" not in f.read().lower()
    with open(gsol.__file__, "r", encoding="utf-8") as f:
        assert "sample_layout" not in f.read().lower()

    # Simulate environment where sample_layout.json is completely unavailable
    orig_exists = Path.exists

    def mocked_exists(path_self: Path) -> bool:
        if "sample_layout.json" in str(path_self):
            return False
        return orig_exists(path_self)

    with patch.object(Path, "exists", side_effect=mocked_exists):
        _, result = solver.solve_with_result(industrial_10_problem, config=generator_config)
        assert result.success is True
        assert result.placed_department_count == 10
        assert result.layout_signature == EXPECTED_SIGNATURE


# ---------------------------------------------------------------------------
# 3. Saved Layout File Verification
# ---------------------------------------------------------------------------

def test_03_saved_layout_file_exists_and_loads():
    """data/examples/generated_industrial_10.json exists, contains all required schema fields, and loads."""
    assert SAVED_LAYOUT_PATH.exists(), f"File missing at {SAVED_LAYOUT_PATH}"

    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Required metadata fields
    assert data["problem_id"] == "FLP_INDUSTRIAL_10"
    assert "generator_version" in data
    assert "configuration" in data
    assert data["configuration"]["strategy"] == "guillotine_row_packing"
    assert data["layout_signature"] == EXPECTED_SIGNATURE
    assert "validation" in data
    assert data["validation"]["is_valid"] is True
    assert data["validation"]["total_overlap_area"] == 0.0
    assert "placements" in data
    assert len(data["placements"]) == 10

    # Load into ContinuousLayout domain model
    layout = ContinuousLayout.model_validate(data)
    assert len(layout.placements) == 10
    assert layout.facility_width == 150.0
    assert layout.facility_height == 80.0


def test_04_saved_layout_completeness_and_dimensions(industrial_10_problem: FacilityLayoutProblem):
    """Saved layout contains all 10 departments and satisfies exact area and dimension bounds."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    depts_map = {d.id: d for d in industrial_10_problem.departments}
    assert len(layout.placements) == 10

    for dept_id, dept in depts_map.items():
        assert dept_id in layout.placements, f"Missing department {dept_id}"
        p = layout.placements[dept_id]

        # Area conservation within 0.05%
        actual_area = p.width * p.height
        assert abs(actual_area - dept.required_area) / dept.required_area < 0.001

        # Dimension bounds
        if dept.min_width:
            assert p.width >= dept.min_width - 1e-4
        if dept.max_width:
            assert p.width <= dept.max_width + 1e-4
        if dept.min_height:
            assert p.height >= dept.min_height - 1e-4
        if dept.max_height:
            assert p.height <= dept.max_height + 1e-4

        # Aspect ratio bounds
        aspect_ratio = max(p.width / p.height, p.height / p.width)
        max_ar = dept.max_aspect_ratio or 3.0
        assert aspect_ratio <= max_ar + 1e-4


def test_05_saved_layout_feasibility_validation(industrial_10_problem: FacilityLayoutProblem):
    """Saved layout passes strict geometric validation with zero overlaps and zero boundary violations."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    val = LayoutValidator.validate(industrial_10_problem, layout)
    assert val.is_valid is True
    assert val.total_overlap_area == 0.0
    assert len(val.errors) == 0

    # Check plant boundaries explicitly
    for p in layout.placements.values():
        assert p.left >= -1e-4
        assert p.bottom >= -1e-4
        assert p.right <= 150.0 + 1e-4
        assert p.top <= 80.0 + 1e-4


def test_06_saved_layout_signature_consistency():
    """Layout signature generated from saved layout matches the generator output signature."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    computed_sig = generate_layout_signature(layout)
    assert computed_sig == EXPECTED_SIGNATURE
    assert data["layout_signature"] == computed_sig


# ---------------------------------------------------------------------------
# 4. CRAFT Integration Tests
# ---------------------------------------------------------------------------

def test_07_craft_accepts_generated_layout(industrial_10_problem: FacilityLayoutProblem):
    """CRAFT improvement algorithm accepts the generated layout without validation error."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    craft = CRAFTAlgorithm()
    solution, craft_res = craft.solve_with_result(
        industrial_10_problem,
        layout,
        max_iterations=50,
        allow_rotation=True,
    )

    assert solution is not None
    assert craft_res.is_complete is True
    assert craft_res.is_feasible is True
    assert len(craft_res.final_layout.placements) == 10


def test_08_craft_does_not_increase_mhc(industrial_10_problem: FacilityLayoutProblem):
    """CRAFT improvement heuristic strictly guarantees non-increasing MHC (final_mhc <= initial_mhc)."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    craft = CRAFTAlgorithm()
    _, craft_res = craft.solve_with_result(
        industrial_10_problem,
        layout,
        max_iterations=50,
        allow_rotation=True,
    )

    assert craft_res.final_mhc <= craft_res.initial_mhc + 1e-4
    assert craft_res.absolute_improvement >= -1e-4


def test_09_craft_improvement_calculation_and_termination(industrial_10_problem: FacilityLayoutProblem):
    """CRAFT correctly evaluates all eligible pairs and honestly reports NO_IMPROVING_SWAP when none improve."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    layout = ContinuousLayout.model_validate(data)

    craft = CRAFTAlgorithm()
    _, craft_res = craft.solve_with_result(
        industrial_10_problem,
        layout,
        max_iterations=50,
        allow_rotation=True,
        trace_level="DETAILED",
    )

    # In this layout, exactly 2 pairs have equal dimensions:
    # 1. (DEP_CUTTING, DEP_SHIPPING)
    # 2. (DEP_FINISHED_GOODS, DEP_RAW_MATERIAL)
    # Both result in cost increases; therefore 0 swaps accepted
    assert craft_res.termination_reason == CRAFTTerminationReason.NO_IMPROVING_SWAP.value
    assert craft_res.iterations == 1
    assert len(craft_res.accepted_swaps) == 0
    assert craft_res.percentage_improvement == 0.0
    assert craft_res.initial_mhc == pytest.approx(180263.9594, rel=1e-3)
    assert craft_res.final_mhc == pytest.approx(180263.9594, rel=1e-3)

    # Verify candidate evaluations detail
    assert len(craft_res.trace.steps) == 1
    step = craft_res.trace.steps[0]
    assert step.candidate_pairs == 2
    assert step.feasible_candidates == 2
    assert step.candidate_evaluations is not None
    for cand in step.candidate_evaluations:
        assert cand["improvement"] < 0.0, f"Expected non-improving swap for {cand['pair']}"


# ---------------------------------------------------------------------------
# 5. Three-Way Multi-Criteria Comparison
# ---------------------------------------------------------------------------

def test_10_consistent_evaluation_config_three_way_comparison(industrial_10_problem: FacilityLayoutProblem):
    """Manual baseline, Guillotine generated, and Guillotine + CRAFT layouts evaluated with identical config."""
    # A. Manual Baseline
    with open(BASELINE_LAYOUT_PATH, "r", encoding="utf-8") as f:
        base_data = json.load(f)
    layout_a = ContinuousLayout.model_validate(base_data)

    # B. Guillotine Generated
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        gen_data = json.load(f)
    layout_b = ContinuousLayout.model_validate(gen_data)

    # C. Guillotine + CRAFT
    craft = CRAFTAlgorithm()
    _, craft_res = craft.solve_with_result(industrial_10_problem, layout_b, max_iterations=50, allow_rotation=True)
    layout_c = craft_res.final_layout

    eval_config = EvaluationConfig()
    engine = EvaluationEngine(config=eval_config)

    rep_a = engine.evaluate(industrial_10_problem, layout_a)
    rep_b = engine.evaluate(industrial_10_problem, layout_b)
    rep_c = engine.evaluate(industrial_10_problem, layout_c)

    # All three are complete and feasible (zero hard violations)
    for rep in [rep_a, rep_b, rep_c]:
        assert rep.complete_layout is True
        assert rep.is_feasible is True
        assert rep.hard_violation_count == 0

    # Layout B and C must match identically since CRAFT found zero improving swaps
    assert rep_b.objective_values["material_handling_cost"] == rep_c.objective_values["material_handling_cost"]
    assert rep_b.objective_values["flow_distance"] == rep_c.objective_values["flow_distance"]
    assert rep_b.layout_signature == rep_c.layout_signature

    # Manual baseline has lower MHC
    assert rep_a.objective_values["material_handling_cost"] < rep_b.objective_values["material_handling_cost"]


# ---------------------------------------------------------------------------
# 6. Soft Constraint Investigation
# ---------------------------------------------------------------------------

def test_11_soft_constraint_investigation_reporting(industrial_10_problem: FacilityLayoutProblem):
    """Precisely investigates the 1 soft constraint violation observed in the generated layout."""
    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        gen_data = json.load(f)
    layout = ContinuousLayout.model_validate(gen_data)

    engine = EvaluationEngine()
    rep = engine.evaluate(industrial_10_problem, layout)

    assert rep.hard_violation_count == 0
    assert rep.soft_violation_count == 1
    assert len(rep.constraint_violations) == 1

    violation = rep.constraint_violations[0]
    assert violation.constraint_id == "CST_SOFT_VIBRATION_SEP"
    assert violation.classification == ConstraintClassification.SOFT
    assert set(violation.involved_departments) == {"DEP_MACHINING", "DEP_QUALITY"}
    assert violation.penalty == 62500.0

    # Verify positions: DEP_MACHINING [70..130, 0..25] touches DEP_QUALITY [130..150, 0..25]
    p_mach = layout.placements["DEP_MACHINING"]
    p_qual = layout.placements["DEP_QUALITY"]
    assert abs(p_mach.right - p_qual.left) < 1e-4, "Machining and Quality touch along x=130"


# ---------------------------------------------------------------------------
# 7. Reproducible Benchmark Metrics
# ---------------------------------------------------------------------------

def test_12_reproducible_benchmark_results(
    industrial_10_problem: FacilityLayoutProblem,
    generator_config: GeneratorConfig,
):
    """A fresh run of the generator reproduces the exact numerical evaluation metrics of the saved file."""
    solver = FeasibleLayoutGenerator()
    _, res_fresh = solver.solve_with_result(industrial_10_problem, config=generator_config)

    with open(SAVED_LAYOUT_PATH, "r", encoding="utf-8") as f:
        gen_data = json.load(f)
    layout_saved = ContinuousLayout.model_validate(gen_data)

    engine = EvaluationEngine()
    rep_fresh = engine.evaluate(industrial_10_problem, res_fresh.layout)
    rep_saved = engine.evaluate(industrial_10_problem, layout_saved)

    assert rep_fresh.layout_signature == rep_saved.layout_signature
    assert rep_fresh.objective_values["material_handling_cost"] == pytest.approx(rep_saved.objective_values["material_handling_cost"], rel=1e-5)
    assert rep_fresh.objective_values["flow_distance"] == pytest.approx(rep_saved.objective_values["flow_distance"], rel=1e-5)
    assert rep_fresh.soft_violation_count == rep_saved.soft_violation_count
    assert rep_fresh.total_constraint_penalty == rep_saved.total_constraint_penalty
