"""BenchmarkRunner service orchestrating systematic evaluation of CORELAP, ALDEP, and CRAFT."""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import numpy as np

from app.algorithms.aldep.solver import ALDEPAlgorithm
from app.algorithms.corelap.solver import CORELAPAlgorithm
from app.algorithms.craft.solver import CRAFTAlgorithm
from app.benchmark.models import (
    ALDEPCandidateRecord,
    ALDEPProblemSummary,
    BenchmarkComparisonRow,
    BenchmarkConfig,
    BenchmarkResult,
    CORELAPRunRecord,
    CRAFTRunRecord,
)
from app.evaluation.engine import EvaluationEngine
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator
from app.services.problem_service import problem_service


class BenchmarkRunner:
    """Executes fair, reproducible, and academically rigorous benchmark suites across algorithms."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.eval_engine = EvaluationEngine(config=self.config.evaluation_config)

    def run_all(self, run_id: Optional[str] = None) -> BenchmarkResult:
        """Execute full benchmark matrix across configured problems and algorithms."""
        start_timestamp = datetime.now(timezone.utc).isoformat()
        if run_id is None:
            clean_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_id = f"bench_{clean_ts}"

        problems: Dict[str, FacilityLayoutProblem] = {}
        for pid in self.config.problem_ids:
            problems[pid] = problem_service.get_example_problem(pid)

        aldep_summaries: Dict[str, ALDEPProblemSummary] = {}
        all_aldep_candidates: List[ALDEPCandidateRecord] = []
        best_aldep_layouts: Dict[str, Optional[ContinuousLayout]] = {}

        # ---------------------------------------------------------------------
        # 1. ALDEP Benchmark Execution
        # ---------------------------------------------------------------------
        for pid, problem in problems.items():
            summary, candidates, best_layout = self._run_aldep_problem(problem)
            aldep_summaries[pid] = summary
            all_aldep_candidates.extend(candidates)
            best_aldep_layouts[pid] = best_layout

        # ---------------------------------------------------------------------
        # 2. CORELAP Benchmark Execution
        # ---------------------------------------------------------------------
        corelap_records: List[CORELAPRunRecord] = []
        corelap_layouts: Dict[str, Optional[ContinuousLayout]] = {}
        for pid, problem in problems.items():
            rec, layout = self._run_corelap_problem(problem)
            corelap_records.append(rec)
            corelap_layouts[pid] = layout

        # ---------------------------------------------------------------------
        # 3. CRAFT Benchmark Execution (Only on Complete & Feasible Baselines)
        # ---------------------------------------------------------------------
        craft_records: List[CRAFTRunRecord] = []

        # (a) FLP_ACADEMIC_4 baselines
        if "FLP_ACADEMIC_4" in problems:
            p4 = problems["FLP_ACADEMIC_4"]
            # CRAFT from CORELAP
            if corelap_layouts.get("FLP_ACADEMIC_4") is not None:
                cr_corelap = self._run_craft(p4, corelap_layouts["FLP_ACADEMIC_4"], "CORELAP Initial")
                if cr_corelap:
                    craft_records.append(cr_corelap)

            # CRAFT from ALDEP best feasible
            if best_aldep_layouts.get("FLP_ACADEMIC_4") is not None:
                cr_aldep = self._run_craft(p4, best_aldep_layouts["FLP_ACADEMIC_4"], "ALDEP Best Feasible")
                if cr_aldep:
                    craft_records.append(cr_aldep)

        # (b) FLP_MEDIUM_6 baselines
        if "FLP_MEDIUM_6" in problems:
            p6 = problems["FLP_MEDIUM_6"]
            if corelap_layouts.get("FLP_MEDIUM_6") is not None:
                cr_corelap = self._run_craft(p6, corelap_layouts["FLP_MEDIUM_6"], "CORELAP Initial")
                if cr_corelap:
                    craft_records.append(cr_corelap)

        # (c) FLP_INDUSTRIAL_10 baselines (Manual Baseline)
        if "FLP_INDUSTRIAL_10" in problems:
            p10 = problems["FLP_INDUSTRIAL_10"]
            manual_layout = self._load_manual_baseline("FLP_INDUSTRIAL_10")
            if manual_layout is not None:
                cr_manual = self._run_craft(p10, manual_layout, "Manual Baseline")
                if cr_manual:
                    craft_records.append(cr_manual)

        # ---------------------------------------------------------------------
        # 4. Assemble Unified Benchmark Comparison Table
        # ---------------------------------------------------------------------
        comparison_table = self._build_comparison_table(
            problems=problems,
            aldep_summaries=aldep_summaries,
            corelap_records=corelap_records,
            craft_records=craft_records,
        )

        metadata = {
            "execution_environment": "Python 3.12 / Antigravity FLODSS",
            "algorithms_evaluated": ["CORELAP", "ALDEP", "CRAFT"],
            "problem_count": len(problems),
            "aldep_total_candidates_generated": len(all_aldep_candidates),
            "craft_experiments_executed": len(craft_records),
        }

        return BenchmarkResult(
            run_id=run_id,
            timestamp=start_timestamp,
            config=self.config,
            comparison_table=comparison_table,
            aldep_summaries=aldep_summaries,
            aldep_candidates=all_aldep_candidates,
            corelap_records=corelap_records,
            craft_records=craft_records,
            metadata=metadata,
        )

    # -------------------------------------------------------------------------
    # Internal Runners
    # -------------------------------------------------------------------------

    def _run_aldep_problem(
        self,
        problem: FacilityLayoutProblem,
    ) -> tuple[ALDEPProblemSummary, List[ALDEPCandidateRecord], Optional[ContinuousLayout]]:
        """Run multi-seed ALDEP experiment budget and aggregate statistics."""
        candidates: List[ALDEPCandidateRecord] = []
        seen_signatures: Dict[str, str] = {}
        best_feasible_layout: Optional[ContinuousLayout] = None
        best_feasible_mhc: float = float("inf")
        total_runtime = 0.0

        for seed in self.config.aldep_seeds:
            t0 = time.perf_counter()
            solver = ALDEPAlgorithm(
                parameters={
                    "random_seed": seed,
                    "number_of_candidates": self.config.aldep_candidates_per_seed,
                    "cell_size": self.config.aldep_cell_size,
                    "strip_width_cells": self.config.aldep_strip_width_cells,
                    "allow_strip_splitting": self.config.aldep_allow_strip_splitting,
                }
            )
            _, solver_res = solver.solve_with_result(problem)
            seed_time = time.perf_counter() - t0
            total_runtime += seed_time

            for c in solver_res.candidates:
                cand_id = f"{problem.id}_s{seed}_c{c.candidate_index}"
                is_dup = c.layout_signature in seen_signatures
                dup_of = seen_signatures.get(c.layout_signature) if is_dup else None
                if not is_dup:
                    seen_signatures[c.layout_signature] = cand_id

                val = LayoutValidator.validate(problem, c.continuous_layout)
                hard_viol = len(val.errors)
                is_feasible = c.is_complete and val.is_valid

                eval_rep = self.eval_engine.evaluate(problem, c.continuous_layout)
                mhc = eval_rep.objective_values.get("material_handling_cost") if is_feasible else None
                flow_dist = eval_rep.objective_values.get("flow_distance") if is_feasible else None
                rel_sat = eval_rep.objective_values.get("relationship_score") if is_feasible else None

                failure_reason = None
                if not c.is_complete:
                    failure_reason = f"Incomplete placement: {len(c.unplaced_departments)} depts unplaced"
                elif not val.is_valid:
                    failure_reason = f"Geometric constraint violation: {val.errors[0]}"

                rec = ALDEPCandidateRecord(
                    problem_id=problem.id,
                    seed=seed,
                    candidate_id=cand_id,
                    candidate_index=c.candidate_index,
                    completion_status=c.is_complete,
                    placed_department_count=c.placed_department_count,
                    total_department_count=c.total_department_count,
                    geometric_feasibility=is_feasible,
                    hard_constraint_violations=hard_viol,
                    layout_signature=c.layout_signature,
                    is_duplicate=is_dup,
                    duplicate_of_id=dup_of,
                    mhc=mhc,
                    flow_distance=flow_dist,
                    relationship_satisfaction=rel_sat,
                    execution_time_seconds=round(seed_time / self.config.aldep_candidates_per_seed, 5),
                    failure_reason=failure_reason,
                )
                candidates.append(rec)

                if is_feasible and mhc is not None and mhc < best_feasible_mhc:
                    best_feasible_mhc = mhc
                    best_feasible_layout = c.continuous_layout

        total_trials = len(candidates)
        complete_count = sum(1 for c in candidates if c.completion_status)
        feasible_count = sum(1 for c in candidates if c.geometric_feasibility)
        unique_count = len(seen_signatures)
        dup_count = sum(1 for c in candidates if c.is_duplicate)

        feasible_mhcs = [c.mhc for c in candidates if c.geometric_feasibility and c.mhc is not None]

        if len(feasible_mhcs) > 0:
            best_mhc = float(np.min(feasible_mhcs))
            worst_mhc = float(np.max(feasible_mhcs))
            median_mhc = float(np.median(feasible_mhcs))
            std_mhc = float(np.std(feasible_mhcs))
            sample_size = len(feasible_mhcs)
            sample_desc = f"Computed over {sample_size} feasible & complete candidates out of {total_trials} generated trials."
        else:
            best_mhc = None
            worst_mhc = None
            median_mhc = None
            std_mhc = None
            sample_size = 0
            sample_desc = f"0 feasible candidates out of {total_trials} generated trials (infeasible candidates strictly excluded from MHC statistics)."

        summary = ALDEPProblemSummary(
            problem_id=problem.id,
            total_trials=total_trials,
            complete_count=complete_count,
            completion_rate=round(complete_count / total_trials, 4),
            feasible_count=feasible_count,
            feasibility_rate=round(feasible_count / total_trials, 4),
            unique_layout_count=unique_count,
            duplicate_count=dup_count,
            best_mhc=best_mhc,
            median_mhc=median_mhc,
            worst_mhc=worst_mhc,
            std_mhc=std_mhc,
            sample_size_mhc=sample_size,
            sample_description=sample_desc,
            best_feasible_signature=generate_layout_signature(best_feasible_layout) if best_feasible_layout else None,
            mean_runtime_seconds=round(total_runtime / total_trials, 5),
            total_runtime_seconds=round(total_runtime, 4),
        )

        return summary, candidates, best_feasible_layout

    def _run_corelap_problem(
        self,
        problem: FacilityLayoutProblem,
    ) -> tuple[CORELAPRunRecord, Optional[ContinuousLayout]]:
        """Run deterministic CORELAP construction heuristic."""
        t0 = time.perf_counter()
        solver = CORELAPAlgorithm()
        solution = solver.solve(problem)
        runtime = time.perf_counter() - t0

        cont_layout = ContinuousLayout.from_layout_solution(
            solution,
            facility_width=problem.facility.width,
            facility_height=problem.facility.height,
        )

        val = LayoutValidator.validate(problem, cont_layout)
        hard_viol = len(val.errors)
        is_feasible = solution.is_complete and val.is_valid

        mhc: Optional[float] = None
        flow_dist: Optional[float] = None
        rel_score: Optional[float] = None

        if is_feasible:
            eval_rep = self.eval_engine.evaluate(problem, cont_layout)
            mhc = eval_rep.objective_values.get("material_handling_cost")
            flow_dist = eval_rep.objective_values.get("flow_distance")
            rel_score = eval_rep.objective_values.get("relationship_score")

        rec = CORELAPRunRecord(
            problem_id=problem.id,
            selected_mode="classical_adjacency",
            completion=solution.is_complete,
            feasibility=is_feasible,
            placed_department_count=solution.placed_department_count,
            total_department_count=solution.total_department_count,
            unplaced_departments=solution.unplaced_departments,
            mhc=mhc,
            relationship_score=rel_score,
            flow_distance=flow_dist,
            hard_constraint_violations=hard_viol,
            termination_reason=solution.termination_reason,
            failure_diagnostics=solution.metadata.get("failure_reason") if not solution.is_complete else None,
            layout_signature=generate_layout_signature(cont_layout),
            runtime_seconds=round(runtime, 5),
        )

        return rec, (cont_layout if is_feasible else None)

    def _run_craft(
        self,
        problem: FacilityLayoutProblem,
        initial_layout: ContinuousLayout,
        initial_source: str,
    ) -> Optional[CRAFTRunRecord]:
        """Run CRAFT improvement heuristic on a complete and feasible initial layout."""
        # Ensure initial layout is valid
        val = LayoutValidator.validate(problem, initial_layout)
        if not val.is_valid:
            return None

        t0 = time.perf_counter()
        solver = CRAFTAlgorithm(parameters={"max_iterations": self.config.craft_max_iterations})
        _, res = solver.solve_with_result(problem, initial_layout)
        runtime = time.perf_counter() - t0

        return CRAFTRunRecord(
            problem_id=problem.id,
            initial_source=initial_source,
            initial_mhc=round(res.initial_mhc, 2),
            final_mhc=round(res.final_mhc, 2),
            absolute_improvement=round(res.absolute_improvement, 2),
            percentage_improvement=round(res.percentage_improvement, 2),
            accepted_swaps=len(res.accepted_swaps),
            termination_reason=res.termination_reason,
            initial_layout_signature=res.initial_layout_signature,
            final_layout_signature=res.final_layout_signature,
            runtime_seconds=round(runtime, 5),
        )

    def _load_manual_baseline(self, problem_id: str) -> Optional[ContinuousLayout]:
        """Load manual baseline layout for designated problems if available."""
        if problem_id == "FLP_INDUSTRIAL_10":
            sample_layout_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "examples" / "sample_layout.json"
            if sample_layout_path.exists():
                with open(sample_layout_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ContinuousLayout.model_validate(data)
        return None

    def _build_comparison_table(
        self,
        problems: Dict[str, FacilityLayoutProblem],
        aldep_summaries: Dict[str, ALDEPProblemSummary],
        corelap_records: List[CORELAPRunRecord],
        craft_records: List[CRAFTRunRecord],
    ) -> List[BenchmarkComparisonRow]:
        """Assemble comparison rows adhering to Section 6 schema."""
        table: List[BenchmarkComparisonRow] = []

        # 1. Manual Baselines
        if "FLP_INDUSTRIAL_10" in problems:
            p10 = problems["FLP_INDUSTRIAL_10"]
            man_layout = self._load_manual_baseline("FLP_INDUSTRIAL_10")
            if man_layout is not None:
                rep = self.eval_engine.evaluate(p10, man_layout)
                table.append(
                    BenchmarkComparisonRow(
                        algorithm="Manual Baseline",
                        problem_id="FLP_INDUSTRIAL_10",
                        run_or_seed="Expert Engineering Layout",
                        complete=True,
                        feasible=True,
                        mhc=round(rep.objective_values.get("material_handling_cost", 0.0), 2),
                        flow_distance=round(rep.objective_values.get("flow_distance", 0.0), 2),
                        relationship_satisfaction=round(rep.objective_values.get("relationship_score", 0.0), 2),
                        constraint_violations=0,
                        runtime_seconds=0.0,
                        notes="Complete reference manual layout",
                    )
                )

        # 2. CORELAP rows
        for cr in corelap_records:
            note = "Deterministic construction"
            if not cr.completion:
                note = f"INCOMPLETE ({cr.placed_department_count}/{cr.total_department_count} placed). Excluded from score ranking."
            elif not cr.feasibility:
                note = "Complete with geometric warnings. Excluded from feasible ranking."
            table.append(
                BenchmarkComparisonRow(
                    algorithm="CORELAP",
                    problem_id=cr.problem_id,
                    run_or_seed="Deterministic",
                    complete=cr.completion,
                    feasible=cr.feasibility,
                    mhc=round(cr.mhc, 2) if cr.mhc is not None else None,
                    flow_distance=round(cr.flow_distance, 2) if cr.flow_distance is not None else None,
                    relationship_satisfaction=round(cr.relationship_score, 2) if cr.relationship_score is not None else None,
                    constraint_violations=cr.hard_constraint_violations,
                    runtime_seconds=cr.runtime_seconds,
                    notes=note,
                )
            )

        # 3. ALDEP summary rows
        for pid, asumm in aldep_summaries.items():
            if asumm.feasible_count > 0:
                note = f"Best feasible of {asumm.total_trials} trials (Feasibility: {asumm.feasibility_rate * 100:.1f}%)"
            else:
                note = f"0 feasible of {asumm.total_trials} trials (Completion: {asumm.completion_rate * 100:.1f}%, Feasibility: 0.0%). Excluded from ranking."

            table.append(
                BenchmarkComparisonRow(
                    algorithm="ALDEP (Best Feasible)",
                    problem_id=pid,
                    run_or_seed=f"5 Seeds ({asumm.total_trials} trials)",
                    complete=asumm.complete_count > 0,
                    feasible=asumm.feasible_count > 0,
                    mhc=round(asumm.best_mhc, 2) if asumm.best_mhc is not None else None,
                    flow_distance=None,  # Detailed candidate table has individual flow_distance
                    relationship_satisfaction=None,
                    constraint_violations=0 if asumm.feasible_count > 0 else 1,
                    runtime_seconds=asumm.total_runtime_seconds,
                    notes=note,
                )
            )

        # 4. CRAFT rows
        for cr in craft_records:
            table.append(
                BenchmarkComparisonRow(
                    algorithm=f"CRAFT (from {cr.initial_source})",
                    problem_id=cr.problem_id,
                    run_or_seed=f"{cr.accepted_swaps} swaps",
                    complete=True,
                    feasible=True,
                    mhc=round(cr.final_mhc, 2),
                    flow_distance=None,
                    relationship_satisfaction=None,
                    constraint_violations=0,
                    runtime_seconds=cr.runtime_seconds,
                    notes=f"Init MHC: {cr.initial_mhc:.2f} -> Final: {cr.final_mhc:.2f} (-{cr.percentage_improvement:.1f}%)",
                )
            )

        return table
