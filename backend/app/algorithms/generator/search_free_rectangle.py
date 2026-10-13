"""Deterministic depth-first backtracking search engine based on Maximal Empty Rectangles."""

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.algorithms.generator.models import (
    DepartmentOrderingStrategy,
    GeneratorConfig,
    GeneratorResult,
    GeneratorTerminationReason,
)
from app.feasibility.dimension_generator import LegalDimensionGenerator
from app.feasibility.free_rectangles import FreeRectangleDetector
from app.feasibility.models import FreeRectangle, LegalDimension
from app.feasibility.placement_checker import PlacementFeasibilityChecker
from app.models.department import Department
from app.models.geometry import Dimensions2D, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator


class FreeRectangleSearchEngine:
    """Explores rectangular layout combinations using free rectangular regions and backtracking."""

    @classmethod
    def order_departments(
        cls,
        problem: FacilityLayoutProblem,
        strategy: DepartmentOrderingStrategy,
    ) -> List[Department]:
        """Sequence departments for constructive placement."""
        depts = list(problem.departments)

        # Fixed positions MUST always be placed first to reserve their ground truth coordinates
        fixed_depts = [d for d in depts if d.fixed_position is not None]
        non_fixed = [d for d in depts if d.fixed_position is None]

        if strategy == DepartmentOrderingStrategy.MOST_CONSTRAINED_FIRST:
            # Score by area, tight dimension range, aspect ratio restriction
            def constraint_score(d: Department) -> float:
                w_range = (d.max_width or 100.0) - (d.min_width or 1.0)
                ar_score = 10.0 / (d.max_aspect_ratio or 5.0)
                return d.required_area * (1.0 / max(1.0, w_range)) * ar_score

            non_fixed.sort(key=constraint_score, reverse=True)

        elif strategy == DepartmentOrderingStrategy.LARGEST_AREA_FIRST:
            non_fixed.sort(key=lambda d: d.required_area, reverse=True)

        elif strategy == DepartmentOrderingStrategy.FLOW_VOLUME_DESCENDING:
            flow_vol: Dict[str, float] = {d.id: 0.0 for d in depts}
            for fl in problem.flows:
                flow_vol[fl.source_department] = flow_vol.get(fl.source_department, 0.0) + fl.quantity
                flow_vol[fl.target_department] = flow_vol.get(fl.target_department, 0.0) + fl.quantity
            non_fixed.sort(key=lambda d: flow_vol.get(d.id, 0.0), reverse=True)

        elif strategy == DepartmentOrderingStrategy.RELATIONSHIP_WEIGHT_DESCENDING:
            tcr: Dict[str, float] = {d.id: 0.0 for d in depts}
            for rel in problem.relationships:
                weight = rel.relationship_type.weight
                tcr[rel.department_a] = tcr.get(rel.department_a, 0.0) + weight
                tcr[rel.department_b] = tcr.get(rel.department_b, 0.0) + weight
            non_fixed.sort(key=lambda d: tcr.get(d.id, 0.0), reverse=True)

        return fixed_depts + non_fixed

    @classmethod
    def search(
        cls,
        problem: FacilityLayoutProblem,
        config: GeneratorConfig,
    ) -> GeneratorResult:
        """Execute deterministic depth-first search over free rectangles and legal dimensions."""
        start_time = time.time()
        ordered_depts = cls.order_departments(problem, config.ordering_strategy)
        num_depts = len(ordered_depts)

        fac_w = problem.facility.width
        fac_h = problem.facility.height
        reserved_zones = problem.reserved_zones

        # Precompute legal dimensions catalog per department
        dim_catalog: Dict[str, List[LegalDimension]] = {}
        for d in ordered_depts:
            dim_catalog[d.id] = LegalDimensionGenerator.generate_legal_dimensions(
                department=d,
                facility_width=fac_w,
                facility_height=fac_h,
                max_alternatives=config.max_shape_alternatives,
                tolerance=config.tolerance,
            )

        # Search execution metrics
        nodes_explored = 0
        backtracks = 0
        candidates_rejected = 0
        failure_counts: Dict[str, int] = {
            "boundary": 0,
            "overlap": 0,
            "area_mismatch": 0,
            "dimension_bounds": 0,
            "aspect_ratio": 0,
            "fixed_position": 0,
            "reserved_zone": 0,
        }

        # Placements state: dept_id -> ContinuousPlacement
        current_placements: Dict[str, ContinuousPlacement] = {}
        best_partial_count = 0
        best_partial_layout: Optional[ContinuousLayout] = None

        termination_reason = GeneratorTerminationReason.SEARCH_SPACE_EXHAUSTED

        def get_candidates(dept_idx: int) -> List[Tuple[float, float, float, float]]:
            """Generate deduplicated (x, y, w, h) candidates for the target department."""
            nonlocal candidates_rejected
            target_dept = ordered_depts[dept_idx]
            legal_shapes = dim_catalog[target_dept.id]
            if not legal_shapes:
                return []

            candidates: List[Tuple[float, float, float, float]] = []
            seen: Set[Tuple[float, float, float, float]] = set()

            # Fixed position department
            if target_dept.fixed_position is not None:
                fx = target_dept.fixed_position.x
                fy = target_dept.fixed_position.y
                for shape in legal_shapes:
                    cand = (fx, fy, shape.width, shape.height)
                    if cand not in seen:
                        seen.add(cand)
                        candidates.append(cand)
                return candidates

            # Detect free rectangular regions (MERs) in the current layout state
            free_report = FreeRectangleDetector.detect_free_rectangles(
                facility_width=fac_w,
                facility_height=fac_h,
                placements=list(current_placements.values()),
                reserved_zones=reserved_zones,
                tolerance=config.tolerance,
            )

            # Collect existing anchor coordinates for boundary alignment
            existing_xs: Set[float] = {0.0}
            existing_ys: Set[float] = {0.0}
            for p in current_placements.values():
                existing_xs.add(round(p.x, 2))
                existing_xs.add(round(p.right, 2))
                existing_ys.add(round(p.y, 2))
                existing_ys.add(round(p.top, 2))

            for mer in free_report.free_rectangles:
                for shape in legal_shapes:
                    w = shape.width
                    h = shape.height

                    # If shape does not fit inside MER, skip immediately
                    if w > mer.width + config.tolerance or h > mer.height + config.tolerance:
                        candidates_rejected += 1
                        continue

                    # Anchor points within this MER
                    anchor_points = [
                        (mer.x_min, mer.y_min),                                 # Bottom-Left
                        (mer.x_min, round(mer.y_max - h, 2)),                  # Top-Left
                        (round(mer.x_max - w, 2), mer.y_min),                  # Bottom-Right
                    ]

                    # Alignment points along existing neighbor boundaries
                    for ex_x in existing_xs:
                        if mer.x_min <= ex_x <= mer.x_max - w:
                            anchor_points.append((ex_x, mer.y_min))
                    for ex_y in existing_ys:
                        if mer.y_min <= ex_y <= mer.y_max - h:
                            anchor_points.append((mer.x_min, ex_y))

                    for ax, ay in anchor_points:
                        key = (round(ax, 2), round(ay, 2), round(w, 2), round(h, 2))
                        if key not in seen:
                            seen.add(key)
                            candidates.append(key)
                            if len(candidates) >= config.candidate_limit_per_department:
                                break
                    if len(candidates) >= config.candidate_limit_per_department:
                        break

            # Sort candidates: prefer bottom-left coordinates to pack tightly
            candidates.sort(key=lambda c: (c[1], c[0], c[2] * c[3]))
            return candidates[: config.candidate_limit_per_department]

        # Stack-based or recursive DFS
        def dfs(dept_idx: int) -> bool:
            nonlocal nodes_explored, backtracks, candidates_rejected, best_partial_count, best_partial_layout, termination_reason

            nodes_explored += 1

            # Check budget and wall-clock time
            if nodes_explored >= config.max_nodes:
                termination_reason = GeneratorTerminationReason.SEARCH_BUDGET_EXHAUSTED
                return False
            if backtracks >= config.max_backtracks:
                termination_reason = GeneratorTerminationReason.SEARCH_BUDGET_EXHAUSTED
                return False
            if time.time() - start_time >= config.max_runtime_seconds:
                termination_reason = GeneratorTerminationReason.TIMEOUT
                return False

            if dept_idx > best_partial_count:
                best_partial_count = dept_idx
                best_partial_layout = ContinuousLayout(
                    problem_id=problem.id,
                    facility_width=fac_w,
                    facility_height=fac_h,
                    placements=dict(current_placements),
                    reserved_zones=reserved_zones,
                )

            # Base case: All departments placed
            if dept_idx == num_depts:
                termination_reason = GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND
                return True

            dept = ordered_depts[dept_idx]
            candidates = get_candidates(dept_idx)

            if not candidates:
                backtracks += 1
                return False

            for cx, cy, cw, ch in candidates:
                # Rigorous independent verification
                check_res = PlacementFeasibilityChecker.check_placement(
                    department=dept,
                    dimensions=Dimensions2D(width=cw, height=ch),
                    coordinates=Point2D(x=cx, y=cy),
                    facility_width=fac_w,
                    facility_height=fac_h,
                    existing_placements=current_placements,
                    reserved_zones=reserved_zones,
                    tolerance=config.tolerance,
                )

                if not check_res.is_feasible:
                    candidates_rejected += 1
                    for err in check_res.rejection_reasons:
                        if "boundary" in err:
                            failure_counts["boundary"] += 1
                        elif "Overlap" in err:
                            failure_counts["overlap"] += 1
                        elif "Area" in err:
                            failure_counts["area_mismatch"] += 1
                        elif "Aspect" in err:
                            failure_counts["aspect_ratio"] += 1
                        elif "violates" in err or "exceeds" in err:
                            failure_counts["dimension_bounds"] += 1
                        elif "fixed" in err:
                            failure_counts["fixed_position"] += 1
                        elif "reserved" in err:
                            failure_counts["reserved_zone"] += 1
                    continue

                # Place department
                current_placements[dept.id] = ContinuousPlacement(
                    department_id=dept.id,
                    x=cx,
                    y=cy,
                    width=cw,
                    height=ch,
                )

                # Recurse to next department
                if dfs(dept_idx + 1):
                    return True

                # Backtrack
                del current_placements[dept.id]
                backtracks += 1

                # Check if aborted inside child
                if termination_reason in (
                    GeneratorTerminationReason.SEARCH_BUDGET_EXHAUSTED,
                    GeneratorTerminationReason.TIMEOUT,
                ):
                    return False

            return False

        # Execute DFS
        success = dfs(0)
        elapsed = round(time.time() - start_time, 4)

        if success:
            final_layout = ContinuousLayout(
                problem_id=problem.id,
                facility_width=fac_w,
                facility_height=fac_h,
                placements=dict(current_placements),
                reserved_zones=reserved_zones,
            )
            # Central validator double-check
            val_res = LayoutValidator.validate(problem, final_layout)
            if not val_res.is_valid:
                # Strict: If central validator finds any flaw, reject
                success = False
                termination_reason = GeneratorTerminationReason.SEARCH_SPACE_EXHAUSTED
                final_layout = best_partial_layout
        else:
            final_layout = best_partial_layout

        sig = generate_layout_signature(final_layout) if final_layout and success else None
        placed_count = len(final_layout.placements) if final_layout else 0

        return GeneratorResult(
            success=success,
            complete=(placed_count == num_depts),
            feasible=success,
            problem_id=problem.id,
            strategy=config.strategy.value,
            layout=final_layout,
            layout_signature=sig,
            placed_department_count=placed_count,
            total_department_count=num_depts,
            nodes_explored=nodes_explored,
            backtracks=backtracks,
            candidates_rejected=candidates_rejected,
            runtime_seconds=elapsed,
            termination_reason=termination_reason,
            failure_diagnostics=failure_counts,
            metadata={
                "strategy": config.strategy.value,
                "ordering_strategy": config.ordering_strategy.value,
            },
        )
