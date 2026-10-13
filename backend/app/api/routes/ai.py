"""API router for FLODSS Gemini AI Decision Explanation and Local Offline Explainer."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status

from app.ai.gemini_service import GeminiExplanationService
from app.ai.local_explainer import LocalDeterministicExplainer
from app.ai.models import (
    AIExplanationResult,
    DataTransferPreview,
    ExplainGeminiRequest,
    ExplainLocalRequest,
    ExplanationMode,
    GrantConsentRequest,
    GrantConsentResponse,
    PreviewPayloadRequest,
)
from app.ai.sanitizer import PayloadSanitizer, ServerConsentStore
from app.core.config import settings
from app.evaluation.canonical import CanonicalEvaluationService
from app.models.problem import FacilityLayoutProblem
from app.models.representation import ContinuousLayout
from app.models.solution import LayoutSolution
from app.optimization.adaptive import (
    AdaptiveConfig,
    AdaptiveStrategyResult,
    RuleBasedStrategySelector,
    StrategyExecutionEngine,
)
from app.services.layout_normalizer import generate_layout_signature
from app.services.problem_analyzer import ProblemAnalyzer
from app.services.problem_service import problem_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

DATA_EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "data" / "examples"


def _resolve_problem(problem_id: Optional[str] = None) -> FacilityLayoutProblem:
    """Resolve target problem instance from repository or example directory."""
    if not problem_id:
        problem_id = "FLP_INDUSTRIAL_10"

    id_to_file = {
        "FLP_ACADEMIC_4": "sample_academic_4.json",
        "FLP_MEDIUM_6": "sample_medium_plant.json",
        "FLP_INDUSTRIAL_10": "sample_plant.json",
        "FLP_EXPANSION_8": "sample_expansion_8.json",
        "FLP_LOGISTICS_5": "sample_logistics_5.json",
        "HIGH_DENSITY_15": "synthetic_high_density_15.json",
        "HIGH_DENSITY_20": "synthetic_high_density_20.json",
        "CONSTRAINED_FACTORY_12": "synthetic_constrained_factory_12.json",
        "LOGISTICS_FACTORY_15": "synthetic_logistics_factory_15.json",
    }

    if problem_id in id_to_file:
        file_path = DATA_EXAMPLES_DIR / id_to_file[problem_id]
        if file_path.exists():
            return problem_service.load_problem(file_path)

    try:
        return problem_service.load_problem(problem_id)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{problem_id}' could not be resolved: {str(ex)}",
        )


def _load_layout_by_signature_or_default(
    problem: FacilityLayoutProblem,
    signature: Optional[str] = None,
) -> Optional[LayoutSolution]:
    """Search example layouts for a matching signature or return canonical benchmark layout."""
    candidate_files = [
        "ga_optimized_industrial_10.json",
        "generated_industrial_10.json",
        "sample_layout.json",
    ]

    for fname in candidate_files:
        path = DATA_EXAMPLES_DIR / fname
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if it has placements
                placements_dict = data.get("placements")
                if placements_dict and isinstance(placements_dict, dict):
                    # Check signature if specified
                    cl = ContinuousLayout.from_placements_dict(placements_dict)
                    sig = generate_layout_signature(cl)
                    if signature is None or sig == signature or fname == signature:
                        report = CanonicalEvaluationService.evaluate(problem, cl)
                        return LayoutSolution(
                            problem_id=problem.id,
                            placements=placements_dict,
                            metrics={
                                "material_handling_cost": report.material_handling_cost,
                                "flow_distance": report.flow_distance,
                                "relationship_satisfaction": report.relationship_satisfaction_percentage,
                                "soft_penalty": report.soft_penalty,
                                "is_feasible": report.is_feasible,
                            },
                        )
            except Exception as e:
                logger.debug(f"Could not load layout from {fname}: {e}")

    return None


def _build_context_and_payload(
    problem_id: str,
    question_type: Any,
    custom_question: Optional[str],
    layout_signature: Optional[str] = None,
    comparison_signature: Optional[str] = None,
):
    """Build problem context, resolve strategy or layouts, and generate sanitized payload."""
    problem = _resolve_problem(problem_id)

    # Resolve primary layout
    primary_solution = _load_layout_by_signature_or_default(problem, layout_signature)
    comparison_solution = None
    if comparison_signature:
        comparison_solution = _load_layout_by_signature_or_default(problem, comparison_signature)

    # Run quick strategy determination if no solution exists
    strategy_result: Optional[AdaptiveStrategyResult] = None
    if not primary_solution:
        try:
            strategy_result = StrategyExecutionEngine.execute(
                problem=problem,
                config=AdaptiveConfig(allow_ga=False, time_limit_seconds=3.0),
            )
        except Exception as e:
            logger.warning(f"Could not execute strategy engine: {e}")

    payload = PayloadSanitizer.build_sanitized_payload(
        problem=problem,
        question_type=question_type,
        custom_question=custom_question,
        strategy_result=strategy_result,
        solution=primary_solution,
        comparison_solution=comparison_solution,
    )
    return problem, payload


@router.get("/status", summary="Check AI Explanation System Status")
def get_ai_status() -> Dict[str, Any]:
    """Retrieve operational status, active configuration, and mode availability for AI explanations."""
    return {
        "ai_enabled": settings.AI_ENABLED,
        "gemini_model": settings.GEMINI_MODEL,
        "has_api_key": bool(settings.GEMINI_API_KEY),
        "supported_modes": [ExplanationMode.LOCAL.value, ExplanationMode.GEMINI.value],
        "default_mode": ExplanationMode.LOCAL.value,
        "timeout_seconds": settings.GEMINI_TIMEOUT_SECONDS,
        "confidentiality_guarantee": (
            "Source code, coordinates, raw flows, and confidential names are strictly whitelisted and excluded."
        ),
    }


@router.post("/preview-payload", response_model=DataTransferPreview, summary="Preview Sanitized Payload Before Consenting")
def preview_payload(request: PreviewPayloadRequest) -> DataTransferPreview:
    """Generate and inspect sanitized data packet and receive a signed consent token bound to its hash."""
    _, payload = _build_context_and_payload(
        problem_id=request.problem_id,
        question_type=request.question_type,
        custom_question=request.custom_question,
        layout_signature=request.layout_signature,
        comparison_signature=request.comparison_layout_signature,
    )
    return PayloadSanitizer.generate_preview(payload)


@router.post("/explain-local", response_model=AIExplanationResult, summary="Offline Deterministic Decision Explanation")
def explain_local(request: ExplainLocalRequest) -> AIExplanationResult:
    """Execute 100% offline rule-based explanation grounded in canonical metrics without network access."""
    _, payload = _build_context_and_payload(
        problem_id=request.problem_id,
        question_type=request.question_type,
        custom_question=request.custom_question,
        layout_signature=request.layout_signature,
        comparison_signature=request.comparison_layout_signature,
    )

    explanation = LocalDeterministicExplainer.explain(payload)
    return AIExplanationResult(
        mode=ExplanationMode.LOCAL,
        question=payload.question_text,
        explanation=explanation,
        verified_canonical_metrics=payload.canonical_metrics,
        provenance={
            "service": "LocalDeterministicExplainer",
            "offline": True,
            "data_transmission_occurred": False,
            "payload_hash": payload.payload_hash,
        },
        validation_passed=True,
        fallback_to_local_used=False,
    )


@router.post("/grant-consent", response_model=GrantConsentResponse, summary="Explicit Human Consent Grant for Gemini Transmission")
def grant_consent(request: GrantConsentRequest) -> GrantConsentResponse:
    """Record user authorization, bind to client session, and return a single-use token."""
    if not request.consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent acknowledgment checkbox must be explicitly checked.",
        )

    field_permissions = {
        "exact_dimensions": request.opt_in_exact_dimensions,
        "exact_areas": request.opt_in_exact_areas,
        "financial_costs": request.opt_in_financial_costs,
    }
    token_str, expires_at = ServerConsentStore.register_consent(
        payload_hash=request.payload_hash,
        client_session_id=request.client_session_id,
        field_permissions=field_permissions,
    )
    return GrantConsentResponse(
        consent_token=token_str,
        payload_hash=request.payload_hash,
        client_session_id=request.client_session_id,
        expires_at=expires_at,
        single_use=True,
    )


@router.post("/explain-gemini", response_model=AIExplanationResult, summary="Grounded Decision Explanation via Gemini API")
def explain_gemini(request: ExplainGeminiRequest) -> AIExplanationResult:
    """Execute Gemini explanation after cryptographic verification of explicit user consent."""
    _, payload = _build_context_and_payload(
        problem_id=request.problem_id,
        question_type=request.question_type,
        custom_question=request.custom_question,
        layout_signature=request.layout_signature,
        comparison_signature=request.comparison_layout_signature,
    )

    # Verify that requested payload hash matches reconstructed payload
    if request.payload_hash != payload.payload_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payload hash mismatch. The problem parameters or question have changed since preview was generated. "
                f"Expected '{payload.payload_hash}', received '{request.payload_hash}'."
            ),
        )

    service = GeminiExplanationService()
    try:
        result = service.explain(
            payload=payload,
            consent_token=request.consent_token,
            client_session_id=request.client_session_id,
        )
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(ve),
        )
