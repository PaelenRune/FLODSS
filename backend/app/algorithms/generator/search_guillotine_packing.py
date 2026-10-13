"""Guillotine row/bay structured constructive search engine."""

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.algorithms.generator.models import (
    GeneratorConfig,
    GeneratorResult,
    GeneratorTerminationReason,
)
from app.feasibility.dimension_generator import LegalDimensionGenerator
from app.feasibility.models import LegalDimension
from app.feasibility.placement_checker import PlacementFeasibilityChecker
from app.models.department import Department
from app.models.geometry import Dimensions2D, Point2D
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout, ContinuousPlacement
from app.services.layout_normalizer import generate_layout_signature
from app.services.layout_validator import LayoutValidator


class GuillotineRowPackingEngine:
    """Explores bay/row-oriented guillotine partition layouts.
    
    In dense industrial facilities (such as FLP_INDUSTRIAL_10 with 91.7% area utilization),
    human plant designers organize departments along parallel logistics bays or aisles.
    This engine systematically searches valid row heights and horizontal allocations.
    """

    @classmethod
    def search(
        cls,
        problem: FacilityLayoutProblem,
        config: GeneratorConfig,
    ) -> GeneratorResult:
        """Search multi-bay guillotine packing with exact area and dimensional conservation."""
        start_time = time.time()
        fac_w = problem.facility.width
        fac_h = problem.facility.height
        depts = list(problem.departments)
        num_depts = len(depts)

        # Precompute legal dimensions
        dim_catalog: Dict[str, List[LegalDimension]] = {}
        for d in depts:
            dim_catalog[d.id] = LegalDimensionGenerator.generate_legal_dimensions(
                department=d,
                facility_width=fac_w,
                facility_height=fac_h,
                max_alternatives=config.max_shape_alternatives,
                tolerance=config.tolerance,
            )

        nodes_explored = 0
        backtracks = 0
        candidates_rejected = 0
        failure_counts: Dict[str, int] = {
            "boundary": 0,
            "overlap": 0,
            "area_mismatch": 0,
            "dimension_bounds": 0,
            "aspect_ratio": 0,
            "row_capacity": 0,
        }

        termination_reason = GeneratorTerminationReason.SEARCH_SPACE_EXHAUSTED
        best_layout: Optional[ContinuousLayout] = None
        best_placed_count = 0

        # Candidate bay heights: test 1-row, 2-row (e.g. 50/50, 40/40), and 3-row configurations
        bay_height_options: List[List[float]] = []
        if num_depts <= 4:
            bay_height_options.append([fac_h])  # Single row
        # 2-bay partitions (e.g. [fac_h / 2, fac_h / 2], [40.0, 40.0], [fac_h * 0.45, fac_h * 0.55])
        half_h = round(fac_h / 2.0, 2)
        bay_height_options.append([half_h, half_h])
        if fac_h >= 60.0:
            bay_height_options.append([round(fac_h * 0.4, 2), round(fac_h * 0.6, 2)])
            bay_height_options.append([round(fac_h * 0.6, 2), round(fac_h * 0.4, 2)])
        if num_depts >= 8 and fac_h >= 60.0:
            third_h = round(fac_h / 3.0, 2)
            bay_height_options.append([third_h, third_h, round(fac_h - 2 * third_h, 2)])

        # Fixed position departments must be honored
        fixed_depts = {d.id: d for d in depts if d.fixed_position is not None}

        # Try bay height configurations
        for bay_heights in bay_height_options:
            num_bays = len(bay_heights)
            bay_y_offsets: List[float] = [0.0]
            for bh in bay_heights[:-1]:
                bay_y_offsets.append(round(bay_y_offsets[-1] + bh, 2))

            # Department assignment to bays:
            # We sort departments by area descending, and use backtracking to place into bays
            sorted_depts = sorted(depts, key=lambda d: d.required_area, reverse=True)

            placements: Dict[str, ContinuousPlacement] = {}
            bay_current_x = [0.0 for _ in range(num_bays)]

            def can_fit_in_bay(dept: Department, bay_idx: int) -> Optional[Tuple[float, float, float, float]]:
                """Find best legal dimension of dept that fits in bay bay_idx."""
                nonlocal candidates_rejected
                bh = bay_heights[bay_idx]
                bx = bay_current_x[bay_idx]
                by = bay_y_offsets[bay_idx]

                if dept.id in fixed_depts:
                    fx = dept.fixed_position.x
                    fy = dept.fixed_position.y
                    # Check if matches this bay
                    for shape in dim_catalog[dept.id]:
                        if abs(fy - by) < config.tolerance and (fx + shape.width <= fac_w + config.tolerance):
                            return (fx, fy, shape.width, shape.height)
                    return None

                # Search legal dimensions that fit within bay height
                for shape in dim_catalog[dept.id]:
                    w = shape.width
                    h = shape.height
                    # Does height fit within bay height?
                    if h <= bh + config.tolerance and (bx + w <= fac_w + config.tolerance):
                        return (bx, by, w, h)

                candidates_rejected += 1
                return None

            def pack_dept(idx: int) -> bool:
                nonlocal nodes_explored, backtracks, candidates_rejected, best_placed_count, best_layout, termination_reason

                nodes_explored += 1
                if nodes_explored >= config.max_nodes or backtracks >= config.max_backtracks:
                    termination_reason = GeneratorTerminationReason.SEARCH_BUDGET_EXHAUSTED
                    return False
                if time.time() - start_time >= config.max_runtime_seconds:
                    termination_reason = GeneratorTerminationReason.TIMEOUT
                    return False

                if idx > best_placed_count:
                    best_placed_count = idx
                    best_layout = ContinuousLayout(
                        problem_id=problem.id,
                        facility_width=fac_w,
                        facility_height=fac_h,
                        placements=dict(placements),
                        reserved_zones=problem.reserved_zones,
                    )

                if idx == num_depts:
                    termination_reason = GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND
                    return True

                target_dept = sorted_depts[idx]

                # Try each bay
                for b_idx in range(num_bays):
                    cand = can_fit_in_bay(target_dept, b_idx)
                    if not cand:
                        continue

                    cx, cy, cw, ch = cand

                    # Check placement feasibility with existing
                    chk = PlacementFeasibilityChecker.check_placement(
                        department=target_dept,
                        dimensions=Dimensions2D(width=cw, height=ch),
                        coordinates=Point2D(x=cx, y=cy),
                        facility_width=fac_w,
                        facility_height=fac_h,
                        existing_placements=placements,
                        reserved_zones=problem.reserved_zones,
                        tolerance=config.tolerance,
                    )

                    if not chk.is_feasible:
                        candidates_rejected += 1
                        continue

                    # Place
                    placements[target_dept.id] = ContinuousPlacement(
                        department_id=target_dept.id,
                        x=cx,
                        y=cy,
                        width=cw,
                        height=ch,
                    )
                    prev_x = bay_current_x[b_idx]
                    bay_current_x[b_idx] = round(cx + cw, 2)

                    if pack_dept(idx + 1):
                        return True

                    # Backtrack
                    del placements[target_dept.id]
                    bay_current_x[b_idx] = prev_x
                    backtracks += 1

                return False

            if pack_dept(0):
                break

        elapsed = round(time.time() - start_time, 4)
        success = (best_placed_count == num_depts)

        if success and best_layout:
            val = LayoutValidator.validate(problem, best_layout)
            if not val.is_valid:
                success = False

        sig = generate_layout_signature(best_layout) if best_layout and success else None

        return GeneratorResult(
            success=success,
            complete=(best_placed_count == num_depts),
            feasible=success,
            problem_id=problem.id,
            strategy=config.strategy.value,
            layout=best_layout,
            layout_signature=sig,
            placed_department_count=best_placed_count,
            total_department_count=num_depts,
            nodes_explored=nodes_explored,
            backtracks=backtracks,
            candidates_rejected=candidates_rejected,
            runtime_seconds=elapsed,
            termination_reason=termination_reason if not success else GeneratorTerminationReason.SUCCESS_FEASIBLE_FOUND,
            failure_diagnostics=failure_counts,
            metadata={"strategy": config.strategy.value},
        )
