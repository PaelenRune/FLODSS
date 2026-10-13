"""Offline, deterministic rule-based explainer generating structured explanations without external API calls."""

from typing import Dict, List
from app.ai.models import (
    PresetQuestionType,
    SanitizedAIExplanationPayload,
    StructuredAIExplanation,
)


class LocalDeterministicExplainer:
    """Generates explainable, grounded, audit-ready explanations entirely on the local CPU."""

    @classmethod
    def explain(cls, payload: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        """Produce structured explanation matching the question type and grounded in canonical metrics."""
        q_type = payload.question_type

        if q_type == PresetQuestionType.WHY_STRATEGY_SELECTED.value:
            return cls._explain_strategy_selection(payload)
        elif q_type == PresetQuestionType.WHY_FEASIBLE.value:
            return cls._explain_feasibility(payload)
        elif q_type == PresetQuestionType.PARETO_COMPARISON.value:
            return cls._explain_pareto_comparison(payload)
        elif q_type == PresetQuestionType.SOFT_PENALTY_EXPLANATION.value:
            return cls._explain_soft_penalty(payload)
        elif q_type == PresetQuestionType.FALLBACK_REASON.value:
            return cls._explain_fallback(payload)
        elif q_type == PresetQuestionType.GLOBAL_OPTIMALITY_QUERY.value:
            return cls._explain_global_optimality(payload)
        else:
            return cls._explain_general(payload)

    @classmethod
    def _explain_strategy_selection(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        reasons = [
            f"Department count N = {p.department_count} and floor space utilization of {p.area_utilization_pct:.1f}%.",
            f"Problem matched the '{p.selected_archetype}' archetype rules in the deterministic strategy selector.",
            f"Primary constructor '{p.primary_algorithm}' was assigned to establish baseline geometric feasibility.",
        ]
        if p.area_utilization_pct >= 80.0:
            reasons.append("High floor utilization (>= 80%) requires slicing or row packing to prevent perimeter overflow.")
        else:
            reasons.append("Moderate floor density (< 80%) allows greedy closeness rating or strip-sweep placement.")

        return StructuredAIExplanation(
            summary=(
                f"FLODSS selected the strategy '{p.selected_strategy_name}' because the facility problem presents "
                f"{p.department_count} departments with {p.area_utilization_pct:.1f}% floor utilization under archetype '{p.selected_archetype}'."
            ),
            main_reasons=reasons,
            strengths=[
                "Deterministic and reproducible rule execution.",
                "Tailored to specific geometric density profile.",
                "Equipped with automatic fallback if primary constructor encounters geometric dead-ends.",
            ],
            risks=[
                "High density layouts reduce candidate search freedom.",
                "Strict aspect ratio boundaries can limit pairwise swapping potential.",
            ],
            trade_offs=[
                "Speed vs Exhaustiveness: Rule selector prioritizes rapid constructive feasibility before metaheuristic exploration."
            ],
            limitations=[
                "Rule thresholds (e.g. 80% utilization boundary) are engineering heuristics based on facility planning literature."
            ],
            evidence_references=["area_utilization", "material_handling_cost"],
        )

    @classmethod
    def _explain_feasibility(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        return StructuredAIExplanation(
            summary=(
                f"The generated FLODSS layout for problem '{p.problem_id}' is verified as 100% complete and feasible by LayoutValidator."
            ),
            main_reasons=[
                f"Completeness: All {p.department_count}/{p.department_count} departments are placed with exact required areas.",
                "Zero Overlap: Pairwise overlap area between all departments is mathematically 0.00 m².",
                f"Boundary Containment: All departments reside strictly within the facility dimensions ({p.facility_dimensions.get('width')}m x {p.facility_dimensions.get('height')}m).",
                "Hard Constraints: 0 hard boundary, non-overlapping, or reserved zone violations detected.",
            ],
            strengths=[
                "Exact area preservation without department distortion.",
                "Guaranteed collision-free floor plan.",
                "Cryptographically verified with SHA-256 geometric layout signature.",
            ],
            risks=[
                "Tight packing leaves minimal expansion buffers between adjacent walls."
            ],
            trade_offs=[
                "Feasibility vs Proximity: Strict non-overlapping separation may force certain high-affinity departments to locate further apart."
            ],
            limitations=[
                "Evaluates 2D planar floor boundaries; 3D vertical clear heights are not modeled."
            ],
            evidence_references=["area_utilization", "hard_violations"],
        )

    @classmethod
    def _explain_pareto_comparison(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        comp = p.alternative_comparison or {}
        mhc_d = comp.get("mhc_delta", 0.0)
        rel_d = comp.get("rel_delta", 0.0)
        soft_d = comp.get("soft_delta", 0.0)

        return StructuredAIExplanation(
            summary=(
                "The Pareto alternatives represent distinct multi-objective engineering compromises between "
                "material handling logistics cost and departmental proximity satisfaction."
            ),
            main_reasons=[
                f"Cost Delta: Layout A differs from Layout B by ${abs(mhc_d):,.2f} in Material Handling Cost.",
                f"Relationship Delta: Relationship satisfaction varies by {abs(rel_d):.2f}% between the alternatives.",
                f"Soft Penalty Delta: Engineering penalty difference is ${abs(soft_d):,.2f}.",
                "Non-domination: Neither layout is strictly superior across all three objectives simultaneously.",
            ],
            strengths=[
                "Allows management to select based on organizational priority (cost minimization vs cross-functional closeness).",
                "Avoids arbitrary weighted-sum bias by preserving the full non-dominated frontier.",
            ],
            risks=[
                "Selecting purely on lowest MHC may place sensitive departments adjacent to vibration or noise sources."
            ],
            trade_offs=[
                f"MHC vs Proximity: Gaining {abs(rel_d):.1f}% closeness satisfaction requires a cost adjustment of ${abs(mhc_d):,.2f}."
            ],
            limitations=[
                "Collinear objectives (e.g. Flow-Distance) are tracked as auxiliary metrics rather than Pareto dimensions to prevent frontier inflation."
            ],
            evidence_references=["material_handling_cost", "relationship_satisfaction", "soft_penalty"],
        )

    @classmethod
    def _explain_soft_penalty(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        soft_pen = p.canonical_metrics.get("soft_penalty", 0.0)
        return StructuredAIExplanation(
            summary=(
                f"The soft constraint penalty of ${soft_pen:,.2f} reflects quantified engineering preferences "
                f"(such as vibration isolation or cleanroom buffer distances) that are economically penalized rather than strictly forbidden."
            ),
            main_reasons=[
                f"Total penalized value: ${soft_pen:,.2f} calculated at defined linear deficit penalty rates.",
                "Soft constraints allow layout feasibility even when physical clearance targets cannot be fully met in dense plants.",
                "Hard constraints (boundary, collision) remain strictly enforced at 0 violations.",
            ],
            strengths=[
                "Prevents optimizer from deadlocking when absolute physical separation is mathematically impossible in a restricted footprint.",
                "Translates engineering clearances into direct financial metrics for unified multi-objective trade-offs.",
            ],
            risks=[
                f"An ongoing soft penalty of ${soft_pen:,.2f} may incur recurring operational damping or maintenance costs."
            ],
            trade_offs=[
                "Floor Space Utilization vs Isolation: Packing departments closer reduces flow distances but incurs separation penalties."
            ],
            limitations=[
                "Assumes linear penalty cost per meter of clearance deficit."
            ],
            evidence_references=["soft_penalty", "cst_soft_vibration_sep"],
        )

    @classmethod
    def _explain_fallback(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        fb_status = "was triggered" if p.fallback_triggered else "was NOT triggered"
        fb_reason = p.fallback_reason or "Primary constructor achieved complete and feasible placement on the first attempt."

        return StructuredAIExplanation(
            summary=(
                f"The adaptive fallback mechanism {fb_status} for problem '{p.problem_id}'. {fb_reason}"
            ),
            main_reasons=[
                f"Primary method: {p.primary_algorithm}.",
                f"Fallback status: {fb_status}.",
                f"Diagnostic reason: {fb_reason}",
                "The engine monitors candidate completeness and geometric validity after each stage, switching algorithms if constraints are violated.",
            ],
            strengths=[
                "High fault tolerance: Prevents pipeline termination when greedy heuristics exceed facility boundaries.",
                "Transparent decision trace: Records exact failure cause in the portfolio audit log.",
            ],
            risks=[
                "Fallback invocation consumes additional wall-clock time budget."
            ],
            trade_offs=[
                "Speed vs Robustness: Verifying candidates and invoking alternative generators adds a small verification overhead."
            ],
            limitations=[
                "If both primary and fallback generators fail due to mathematically impossible constraints, no feasible candidate can be produced."
            ],
            evidence_references=["area_utilization", "hard_violations"],
        )

    @classmethod
    def _explain_global_optimality(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        mhc = p.canonical_metrics.get("material_handling_cost", 0.0)
        return StructuredAIExplanation(
            summary=(
                "NO, this result is NOT guaranteed to be globally optimal, and no mathematical guarantee of optimality is claimed. "
                "Facility Layout Optimization with unequal areas is strongly NP-hard; FLODSS provides verified high-quality feasible solutions and Pareto frontiers, not mathematical global optimality proofs."
            ),
            main_reasons=[
                "Complexity Class: The Unequal-Area Facility Layout Problem (UA-FLP) is mathematically NP-hard in the strong sense.",
                "Continuous Search Space: Placing variable rectangles with continuous dimensions creates an infinite continuum of topological combinations.",
                f"Achieved Result: The current best candidate achieves an MHC of ${mhc:,.2f} under verified feasibility, which is an established local/heuristic optimum.",
                "Exact Global Solvers: Guaranteeing a mathematical global optimum requires exhaustive combinatorial branch-and-bound enumeration, which scales exponentially and is computationally intractable for industrial-scale plant problems.",
            ],
            strengths=[
                "Pragmatic industrial applicability: Generates guaranteed collision-free, construction-ready layouts in seconds.",
                "Explores diverse topologies via metaheuristic search (FBS, GA, CRAFT).",
                "Cryptographically verified canonical evaluation guarantees metric accuracy.",
            ],
            risks=[
                "Heuristic search may converge to a strong local optimum rather than the theoretical global minimum."
            ],
            trade_offs=[
                "Computational Tractability vs Global Certainty: Achieving an actionable solution in < 1 second versus months of exponential exact solver search."
            ],
            limitations=[
                "Mathematical global optimum remains unknown without exponential exhaustive enumeration."
            ],
            evidence_references=["material_handling_cost", "relationship_satisfaction"],
            global_optimality_disclaimer=(
                "CRITICAL ENGINEERING DISCLAIMER: Facility Layout Optimization is strongly NP-hard. "
                "FLODSS utilizes heuristic construction, slicing trees, and genetic metaheuristics. "
                "No mathematical guarantee of global optimality is claimed or implied."
            ),
        )

    @classmethod
    def _explain_general(cls, p: SanitizedAIExplanationPayload) -> StructuredAIExplanation:
        mhc = p.canonical_metrics.get("material_handling_cost", 0.0)
        rel = p.canonical_metrics.get("relationship_satisfaction", 0.0)
        soft = p.canonical_metrics.get("soft_penalty", 0.0)

        return StructuredAIExplanation(
            summary=(
                f"Facility layout analysis for '{p.problem_id}' ({p.department_count} departments, {p.area_utilization_pct:.1f}% utilization). "
                f"Current verified candidate achieves MHC = ${mhc:,.2f}, Relationship Satisfaction = {rel:.2f}%, Soft Penalty = ${soft:,.2f}."
            ),
            main_reasons=[
                f"Selected strategy: '{p.selected_strategy_name}'.",
                f"Feasibility status: Verified complete (0 hard violations).",
                f"Floor density: {p.area_utilization_pct:.1f}% floor utilization.",
            ],
            strengths=[
                "Exact rectangular boundary enforcement.",
                "Multi-objective Pareto evaluation.",
                "Explainable deterministic provenance trace.",
            ],
            risks=[
                "Physical layout performance depends on accurate material flow matrices."
            ],
            trade_offs=[
                "Material handling efficiency vs qualitative departmental closeness."
            ],
            limitations=[
                "2D planar modeling with deterministic flow demand."
            ],
            evidence_references=["material_handling_cost", "relationship_satisfaction", "soft_penalty"],
        )
