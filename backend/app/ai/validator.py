"""Strict output validator for AI-generated explanations to prevent hallucinations, fabricated metrics, and false optimality claims."""

import re
from typing import List, Tuple
from app.ai.models import SanitizedAIExplanationPayload, StructuredAIExplanation

ALLOWED_EVIDENCE_METRICS = {
    "material_handling_cost",
    "mhc",
    "flow_distance",
    "relationship_satisfaction",
    "rel_satisfaction",
    "soft_penalty",
    "soft_constraint_penalty",
    "area_utilization",
    "hard_violations",
    "soft_violations",
    "pareto_rank",
    "cst_soft_vibration_sep",
    "cst_boundary",
    "cst_non_overlapping",
}

FORBIDDEN_ALGORITHM_HALLUCINATIONS = [
    r"\bsimulated\s+annealing\b",
    r"\bnsga[-_ ]?ii\b",
    r"\bmilp\b",
    r"\bmixed\s+integer\b",
    r"\bparticle\s+swarm\b",
    r"\btabu\s+search\b",
    r"\bant\s+colony\b",
]

FALSE_OPTIMALITY_CLAIMS = [
    r"\bproven\s+global(ly)?\s+optimal\b",
    r"\bmathematically\s+optimal\b",
    r"\bguaranteed\s+global\s+optimum\b",
    r"\babsolute\s+best\s+possible\s+solution\b",
    r"\bexact\s+optimal\s+solution\b",
]


class ExplanationOutputValidator:
    """Validates structured explanation outputs against canonical payload ground truths."""

    @classmethod
    def validate(
        cls,
        explanation: StructuredAIExplanation,
        payload: SanitizedAIExplanationPayload,
    ) -> Tuple[bool, List[str]]:
        """Perform comprehensive consistency, grounding, and security checks on explanation."""
        errors: List[str] = []

        # 1. Validate Evidence References
        for ref in explanation.evidence_references:
            normalized_ref = ref.strip().lower()
            if normalized_ref not in ALLOWED_EVIDENCE_METRICS:
                errors.append(f"Invalid or fabricated metric reference: '{ref}'. Evidence must refer strictly to whitelisted canonical metrics.")

        # Combined text for semantic scanning
        combined_text = (
            f"{explanation.summary} "
            f"{' '.join(explanation.main_reasons)} "
            f"{' '.join(explanation.strengths)} "
            f"{' '.join(explanation.risks)} "
            f"{' '.join(explanation.trade_offs)} "
            f"{' '.join(explanation.limitations)}"
        ).lower()

        # 2. Check for Fabricated Algorithms
        for pattern in FORBIDDEN_ALGORITHM_HALLUCINATIONS:
            if re.search(pattern, combined_text):
                errors.append(f"Forbidden or fabricated algorithm mentioned: matching pattern '{pattern}'. FLODSS v1 only supports implemented algorithms.")

        # 3. Check for Unsupported Global Optimality Claims
        for pattern in FALSE_OPTIMALITY_CLAIMS:
            if re.search(pattern, combined_text):
                errors.append(f"Unsupported mathematical optimality claim detected: matching '{pattern}'. FLODSS does not claim global optimality for NP-hard heuristics.")

        # 4. Zero-Tolerance Numeric Grounding Checks
        payload_mhc = payload.canonical_metrics.get("material_handling_cost", 0.0)
        payload_soft = payload.canonical_metrics.get("soft_penalty", 0.0)
        allowed_monetary = [payload_mhc, payload_soft]

        if payload.alternative_comparison:
            allowed_monetary.append(abs(payload.alternative_comparison.get("mhc_delta", 0.0)))
            allowed_monetary.append(abs(payload.alternative_comparison.get("soft_delta", 0.0)))

        # 4a. Strict Dollar Amount Check (Zero Tolerance: < 1.0 or relative < 0.005)
        dollar_matches = re.findall(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)", combined_text)
        for match_str in dollar_matches:
            try:
                val = float(match_str.replace(",", ""))
                if val > 10.0:  # Check any non-trivial financial figure
                    is_grounded = any(
                        (abs(val - allowed) < 1.0) or (allowed > 0 and abs(val - allowed) / allowed < 0.005)
                        for allowed in allowed_monetary if allowed > 0
                    )
                    if not is_grounded:
                        errors.append(f"Ungrounded financial figure detected: '${match_str}'. Cost claims must strictly match calculated canonical metrics.")
            except ValueError:
                continue

        # 4b. Department Count Grounding Check
        dept_count_matches = re.findall(r"\b([0-9]{1,3})\s+(?:departments?|depts?)\b", combined_text)
        for match_str in dept_count_matches:
            try:
                dept_val = int(match_str)
                if dept_val != payload.department_count:
                    errors.append(f"Department count hallucination: mentioned {dept_val} departments, expected exactly {payload.department_count}.")
            except ValueError:
                continue

        # 4c. Percentage Grounding Check (Utilization, REL satisfaction, deltas)
        pct_matches = re.findall(r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%", combined_text)
        allowed_pcts = [
            payload.area_utilization_pct,
            payload.canonical_metrics.get("relationship_satisfaction", 0.0),
            100.0,  # 100% completion/feasibility
            80.0,   # Archetype density boundary threshold
            0.0,
        ]
        if payload.alternative_comparison:
            allowed_pcts.append(abs(payload.alternative_comparison.get("rel_delta", 0.0)))

        for match_str in pct_matches:
            try:
                pct_val = float(match_str)
                # If percentage is non-trivial (> 1.0%), verify it matches one of the canonical percentages within 0.5%
                if pct_val > 1.0:
                    is_grounded_pct = any(abs(pct_val - allowed) < 0.5 for allowed in allowed_pcts)
                    if not is_grounded_pct:
                        errors.append(f"Ungrounded percentage detected: '{match_str}%'. Percentages must strictly match canonical utilization or proximity satisfaction.")
            except ValueError:
                continue

        # 5. Mandatory Global Optimality Disclaimer Verification
        if not explanation.global_optimality_disclaimer or len(explanation.global_optimality_disclaimer.strip()) < 15:
            errors.append("Missing mandatory global optimality disclaimer acknowledging NP-hard heuristic boundaries.")

        return len(errors) == 0, errors
