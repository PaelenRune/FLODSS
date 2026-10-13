"""Gemini API Decision Explanation Service with strict grounding, output validation, and local fallback."""

import json
import logging
from typing import Any, Dict, Optional

from app.ai.local_explainer import LocalDeterministicExplainer
from app.ai.models import (
    AIExplanationResult,
    ExplanationMode,
    SanitizedAIExplanationPayload,
    StructuredAIExplanation,
)
from app.ai.sanitizer import PayloadSanitizer
from app.ai.validator import ExplanationOutputValidator
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are an industrial engineering decision explanation assistant for FLODSS (Facility Layout Optimization Decision Support System).
Your role is EXCLUSIVELY to explain layout optimization results, algorithm selections, engineering trade-offs, and geometric constraints based ONLY on the provided sanitized payload.

STRICT OPERATIONAL BOUNDARIES:
1. GROUNDING: Ground all statements in the provided canonical metrics and problem parameters. Never invent numerical values.
2. NO FORBIDDEN ALGORITHMS: FLODSS v1 currently implements CORELAP, ALDEP, CRAFT, Feasible Rectangular Generator (Guillotine Row Packing), and Genetic Algorithm v1. NEVER mention Simulated Annealing, NSGA-II, MILP (Mixed Integer Linear Programming), Particle Swarm, or any other unlisted algorithms.
3. NO GLOBAL OPTIMALITY: The Facility Layout Problem is strongly NP-hard. Do NOT claim the layout is mathematically or globally optimal.
4. FINANCIAL FIGURES: Any dollar or cost claims must strictly align with the provided canonical material handling cost ($) or soft constraint penalty ($).
5. EVIDENCE REFERENCES: Include references to the relevant canonical metrics you cited (e.g., 'material_handling_cost', 'relationship_satisfaction', 'soft_penalty', 'area_utilization').
6. DISCLAIMER: Always provide the mandatory disclaimer that FLODSS uses heuristic and metaheuristic approaches without mathematical guarantees of global optimality.
"""


class GeminiExplanationService:
    """Explains FLODSS optimization decisions using Google Gemini API with confidentiality and fallback guarantees."""

    def __init__(
        self,
        client: Optional[Any] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = client

    @property
    def client(self) -> Optional[Any]:
        """Lazy initialization of Google GenAI client if not overridden."""
        if self._client is not None:
            return self._client
        if settings.AI_ENABLED and settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Google GenAI client: {e}")
                self._client = None
        return self._client

    def explain(
        self,
        payload: SanitizedAIExplanationPayload,
        consent_token: str,
        client_session_id: Optional[str] = None,
    ) -> AIExplanationResult:
        """Execute Gemini decision explanation with consent verification, output validation, and automatic fallback."""
        # 1. Verify User Consent Token
        is_valid, consent_error = PayloadSanitizer.verify_consent(
            consent_token_str=consent_token,
            expected_payload_hash=payload.payload_hash,
            client_session_id=client_session_id,
        )
        if not is_valid:
            raise ValueError(f"Unauthorized data transmission: {consent_error}")

        # 2. Check if AI is enabled and client available
        if not settings.AI_ENABLED or self.client is None:
            local_exp = LocalDeterministicExplainer.explain(payload)
            return AIExplanationResult(
                mode=ExplanationMode.LOCAL,
                question=payload.question_text,
                explanation=local_exp,
                verified_canonical_metrics=payload.canonical_metrics,
                provenance={
                    "service": "LocalDeterministicExplainer",
                    "reason": "AI_ENABLED is False or GEMINI_API_KEY is not configured",
                    "data_transmission_occurred": False,
                },
                validation_passed=True,
                fallback_to_local_used=True,
                fallback_reason="Gemini AI is disabled or unconfigured in system settings.",
            )

        # 3. Build Prompt & Invocation Config
        prompt = (
            f"User Question: {payload.question_text}\n\n"
            f"Question Type: {payload.question_type}\n\n"
            f"Sanitized Facility Context & Grounded Metrics:\n"
            f"{payload.model_dump_json(indent=2)}\n\n"
            f"Explain this optimization result clearly and rigorously according to your system instructions."
        )

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_json_schema=StructuredAIExplanation.model_json_schema(),
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            raw_text = response.text or "{}"
            explanation_data = json.loads(raw_text)
            structured_exp = StructuredAIExplanation.model_validate(explanation_data)

            # 4. Strict Validation of AI Output
            val_passed, val_errors = ExplanationOutputValidator.validate(structured_exp, payload)
            if not val_passed:
                logger.warning(f"Gemini explanation failed validation: {val_errors}. Falling back to local explainer.")
                local_fallback = LocalDeterministicExplainer.explain(payload)
                return AIExplanationResult(
                    mode=ExplanationMode.LOCAL,
                    question=payload.question_text,
                    explanation=local_fallback,
                    verified_canonical_metrics=payload.canonical_metrics,
                    provenance={
                        "service": "LocalDeterministicExplainer",
                        "validation_errors": val_errors,
                        "data_transmission_occurred": True,
                        "payload_hash": payload.payload_hash,
                    },
                    validation_passed=False,
                    fallback_to_local_used=True,
                    fallback_reason=f"Gemini output failed validation: {'; '.join(val_errors)}",
                )

            return AIExplanationResult(
                mode=ExplanationMode.GEMINI,
                question=payload.question_text,
                explanation=structured_exp,
                verified_canonical_metrics=payload.canonical_metrics,
                provenance={
                    "service": "GoogleGeminiAPI",
                    "model": self.model_name,
                    "payload_hash": payload.payload_hash,
                    "data_transmission_occurred": True,
                },
                validation_passed=True,
                fallback_to_local_used=False,
            )

        except Exception as ex:
            logger.error(f"Error calling Gemini API: {ex}. Falling back to local explainer.")
            local_fallback = LocalDeterministicExplainer.explain(payload)
            return AIExplanationResult(
                mode=ExplanationMode.LOCAL,
                question=payload.question_text,
                explanation=local_fallback,
                verified_canonical_metrics=payload.canonical_metrics,
                provenance={
                    "service": "LocalDeterministicExplainer",
                    "exception": str(ex),
                    "data_transmission_occurred": True,
                    "payload_hash": payload.payload_hash,
                },
                validation_passed=True,
                fallback_to_local_used=True,
                fallback_reason=f"Gemini API call failed ({type(ex).__name__}): {str(ex)}",
            )
