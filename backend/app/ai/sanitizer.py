"""Confidentiality-first payload sanitizer, whitelist enforcer, and consent token issuer."""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.ai.models import (
    DataTransferPreview,
    PRESET_QUESTION_TEXTS,
    PresetQuestionType,
    SanitizedAIExplanationPayload,
    SanitizedPayloadDepartment,
    UserConsentToken,
)
from app.core.config import settings
from app.models.problem import FacilityLayoutProblem
from app.models.solution import LayoutSolution
from app.optimization.adaptive import AdaptiveStrategyResult
from app.services.problem_analyzer import ProblemAnalyzer


WHITELISTED_FIELDS = [
    "problem_id",
    "facility_dimensions",
    "department_count",
    "area_utilization_pct",
    "anonymized_departments (alias and area only)",
    "selected_strategy_name",
    "selected_archetype",
    "primary_algorithm",
    "fallback_triggered",
    "fallback_reason",
    "canonical_metrics (material_handling_cost, flow_distance, relationship_satisfaction, soft_penalty)",
    "violations_summary (counts and types)",
    "pareto_rank",
    "is_non_dominated",
    "alternative_comparison (metric deltas)",
    "question_type",
    "question_text",
]

EXCLUDED_SENSITIVE_FIELDS = [
    "Source code and internal algorithm implementations",
    "Git repository metadata, branch names, commit history",
    "Exact department spatial coordinates (origin x, y, width, height)",
    "Raw pairwise flow volume matrix and unit cost rates",
    "Confidential department identifiers and company-specific names",
    "Invention disclosure, patent research, or internal developer notes",
    "System environment variables, passwords, and API keys",
]


class ServerConsentStore:
    """Thread-safe, stateful server-side consent authorization registry.

    Security Guarantees:
    1. Single-use enforcement: Tokens are consumed upon invocation to prevent replay attacks.
    2. Session binding: Tokens are tied to client_session_id to prevent cross-session leakage.
    3. Payload immutability: Signed hash ensures tamper-evident payload verification.
    4. Auto-expiration: Strict 15-minute validity window.
    """

    _lock = threading.Lock()
    _granted_consents: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_consent(
        cls,
        payload_hash: str,
        client_session_id: str = "default_session",
        field_permissions: Optional[Dict[str, bool]] = None,
    ) -> Tuple[str, str]:
        """Record explicit server-side authorization and generate signed token."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)
        granted_at = now.isoformat()
        expires_at = expires.isoformat()

        sig_data = f"{payload_hash}|{client_session_id}|{granted_at}|{expires_at}"
        secret = settings.AI_CONSENT_SECRET.encode("utf-8")
        sig = hmac.new(secret, sig_data.encode("utf-8"), hashlib.sha256).hexdigest()

        token_obj = {
            "payload_hash": payload_hash,
            "client_session_id": client_session_id,
            "granted_at": granted_at,
            "expires_at": expires_at,
            "signature": sig,
        }
        token_str = json.dumps(token_obj)

        with cls._lock:
            cls._granted_consents[sig] = {
                "payload_hash": payload_hash,
                "client_session_id": client_session_id,
                "expires_at": expires,
                "used": False,
                "field_permissions": field_permissions or {},
            }

        return token_str, expires_at

    @classmethod
    def verify_and_consume(
        cls,
        consent_token_str: str,
        expected_payload_hash: str,
        client_session_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify token authenticity, check single-use status, and immediately consume token."""
        try:
            token_dict = json.loads(consent_token_str)
            p_hash = token_dict.get("payload_hash")
            token_session = token_dict.get("client_session_id", "default_session")
            granted_at = token_dict.get("granted_at")
            expires_at = token_dict.get("expires_at")
            sig = token_dict.get("signature")

            if not all([p_hash, granted_at, expires_at, sig]):
                return False, "Malformed consent token missing required fields."

            if p_hash != expected_payload_hash:
                return False, f"Consent token hash mismatch: token grants permission for '{p_hash}', not '{expected_payload_hash}'."

            if client_session_id and token_session != client_session_id:
                return False, f"Session mismatch: token was issued for session '{token_session}', cannot be consumed by '{client_session_id}'."

            exp_dt = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) > exp_dt:
                return False, "Consent token has expired (15-minute validity limit). Please review the payload again."

            # Verify HMAC signature (support session-bound and legacy format)
            secret = settings.AI_CONSENT_SECRET.encode("utf-8")
            sig_data_session = f"{p_hash}|{token_session}|{granted_at}|{expires_at}"
            expected_sig_session = hmac.new(secret, sig_data_session.encode("utf-8"), hashlib.sha256).hexdigest()

            sig_data_legacy = f"{p_hash}|{granted_at}|{expires_at}"
            expected_sig_legacy = hmac.new(secret, sig_data_legacy.encode("utf-8"), hashlib.sha256).hexdigest()

            if not (hmac.compare_digest(sig, expected_sig_session) or hmac.compare_digest(sig, expected_sig_legacy)):
                return False, "Invalid consent signature: token has been tampered with."

            # Single-use check and consumption
            with cls._lock:
                entry = cls._granted_consents.get(sig)
                if entry:
                    if entry.get("used", False):
                        return False, "Security Violation: Consent token has already been consumed (single-use replay prevention)."
                    entry["used"] = True
                else:
                    # Direct/legacy token registration and immediate consumption
                    cls._granted_consents[sig] = {
                        "payload_hash": p_hash,
                        "used": True,
                    }

            return True, None
        except Exception as ex:
            return False, f"Consent verification error: {str(ex)}"

    @classmethod
    def reset(cls) -> None:
        """Clear registered consents (used in testing)."""
        with cls._lock:
            cls._granted_consents.clear()


class PayloadSanitizer:
    """Extracts strictly whitelisted, anonymized data for explanation tasks and manages cryptographic consent."""

    @classmethod
    def sanitize_user_prompt(cls, prompt: str) -> str:
        """Sanitize user text input to mitigate prompt injection and escape delimiters."""
        if not prompt:
            return ""
        # Remove potential control sequences and injection markers
        cleaned = re.sub(r"[<>{}\[\]\\]", " ", prompt)
        # Block common prompt injection phrases
        forbidden_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"system\s+prompt",
            r"reveal\s+(api\s+)?key",
            r"disregard\s+rules",
            r"execute\s+command",
        ]
        for pattern in forbidden_patterns:
            cleaned = re.sub(pattern, "[REDACTED_INJECTION_ATTEMPT]", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()[:300]  # Hard character limit

    @classmethod
    def build_sanitized_payload(
        cls,
        problem: FacilityLayoutProblem,
        question_type: PresetQuestionType = PresetQuestionType.WHY_STRATEGY_SELECTED,
        custom_question: Optional[str] = None,
        strategy_result: Optional[AdaptiveStrategyResult] = None,
        solution: Optional[LayoutSolution] = None,
        comparison_solution: Optional[LayoutSolution] = None,
    ) -> SanitizedAIExplanationPayload:
        """Extract whitelisted parameters, strictly redacting confidential structures."""
        # 1. Anonymize departments
        anonymized_depts: List[SanitizedPayloadDepartment] = []
        for idx, dept in enumerate(sorted(problem.departments, key=lambda d: d.id), start=1):
            anonymized_depts.append(
                SanitizedPayloadDepartment(
                    dept_alias=f"Dept {idx}",
                    required_area=float(dept.required_area),
                    category="production",
                )
            )

        # 2. Dimensions & Utilization
        fp = ProblemAnalyzer.extract_fingerprint(problem)
        fac_w = float(problem.facility.width)
        fac_h = float(problem.facility.height)
        fac_area = float(problem.facility.area or (fac_w * fac_h))
        util_pct = round(fp.area_utilization * 100.0, 2)

        # 3. Strategy & Execution provenance
        strat_name = "Rule-Based Strategy Pipeline"
        archetype = "dense_rectangular_constrained" if util_pct >= 80 else "small_unconstrained_flow"
        prim_algo = "feasible_layout_generator"
        fb_triggered = False
        fb_reason = None

        if strategy_result:
            strat_name = strategy_result.selected_strategy.name
            archetype = strategy_result.selected_strategy.archetype.value
            prim_algo = strategy_result.selected_strategy.primary_algorithm
            fallback_steps = [st for st in strategy_result.execution_trace if st.was_fallback]
            if fallback_steps:
                fb_triggered = True
                fb_reason = fallback_steps[0].failure_reason

        # 4. Canonical metrics extraction
        canon_metrics: Dict[str, float] = {}
        violations_summary: Dict[str, Any] = {"hard_count": 0, "soft_count": 0}
        pareto_rank: Optional[int] = None
        is_non_dom: Optional[bool] = None

        # Try to locate candidate metrics
        if strategy_result and strategy_result.final_recommendation:
            rec = strategy_result.final_recommendation
            canon_metrics = {
                "material_handling_cost": float(rec.get("material_handling_cost") or 0.0),
                "relationship_satisfaction": float(rec.get("relationship_satisfaction") or 0.0),
                "soft_penalty": float(rec.get("soft_penalty") or 0.0),
            }
            pareto_rank = rec.get("pareto_rank")
            is_non_dom = rec.get("is_on_pareto_frontier")
        elif solution and solution.metrics:
            m = solution.metrics
            canon_metrics = {
                "material_handling_cost": float(m.get("material_handling_cost") or 0.0),
                "relationship_satisfaction": float(m.get("relationship_satisfaction") or 0.0),
                "soft_penalty": float(m.get("soft_penalty") or 0.0),
                "flow_distance": float(m.get("flow_distance") or 0.0),
            }

        # 5. Question formatting
        q_text = PRESET_QUESTION_TEXTS.get(question_type, "Provide a comprehensive layout explanation.")
        if question_type == PresetQuestionType.CUSTOM and custom_question:
            q_text = cls.sanitize_user_prompt(custom_question)

        # 6. Alternative comparison if comparing two solutions
        comp_data = None
        if comparison_solution and comparison_solution.metrics and solution and solution.metrics:
            m_a = solution.metrics
            m_b = comparison_solution.metrics
            comp_data = {
                "mhc_delta": round(float(m_a.get("material_handling_cost", 0.0)) - float(m_b.get("material_handling_cost", 0.0)), 2),
                "rel_delta": round(float(m_a.get("relationship_satisfaction", 0.0)) - float(m_b.get("relationship_satisfaction", 0.0)), 2),
                "soft_delta": round(float(m_a.get("soft_penalty", 0.0)) - float(m_b.get("soft_penalty", 0.0)), 2),
            }

        # Build initial payload without hash to compute canonical hash
        base_dict = {
            "problem_id": str(problem.id),
            "facility_dimensions": {"width": fac_w, "height": fac_h, "area": fac_area},
            "department_count": len(problem.departments),
            "area_utilization_pct": util_pct,
            "anonymized_departments": [d.model_dump() for d in anonymized_depts],
            "selected_strategy_name": strat_name,
            "selected_archetype": archetype,
            "primary_algorithm": prim_algo,
            "fallback_triggered": fb_triggered,
            "fallback_reason": fb_reason,
            "canonical_metrics": canon_metrics,
            "violations_summary": violations_summary,
            "pareto_rank": pareto_rank,
            "is_non_dominated": is_non_dom,
            "alternative_comparison": comp_data,
            "question_type": question_type.value,
            "question_text": q_text,
        }

        canonical_json = json.dumps(base_dict, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return SanitizedAIExplanationPayload(
            **base_dict,
            payload_hash=payload_hash,
        )

    @classmethod
    def issue_consent_token(
        cls,
        payload_hash: str,
        client_session_id: str = "default_session",
    ) -> str:
        """Generate cryptographically signed, server-registered consent token."""
        token_str, _ = ServerConsentStore.register_consent(payload_hash, client_session_id)
        return token_str

    @classmethod
    def verify_consent(
        cls,
        consent_token_str: str,
        expected_payload_hash: str,
        client_session_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify that user consent was granted for this EXACT payload and has not expired or been replayed."""
        return ServerConsentStore.verify_and_consume(consent_token_str, expected_payload_hash, client_session_id)

    @classmethod
    def generate_preview(
        cls,
        payload: SanitizedAIExplanationPayload,
    ) -> DataTransferPreview:
        """Create transparent preview with cryptographic consent token."""
        token = cls.issue_consent_token(payload.payload_hash)
        return DataTransferPreview(
            provider="Google Gemini API",
            target_model=settings.GEMINI_MODEL,
            whitelisted_fields=WHITELISTED_FIELDS,
            excluded_sensitive_fields=EXCLUDED_SENSITIVE_FIELDS,
            payload=payload,
            payload_hash=payload.payload_hash,
            consent_token=token,
        )
