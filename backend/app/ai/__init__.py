"""AI package for layout reasoning, diagnosis, decision support, and grounded decision explanations."""

from app.ai.base import (
    LayoutSuggestion,
    LayoutDiagnosis,
    BaseLayoutAdvisor,
)
from app.ai.gemini_service import GeminiExplanationService
from app.ai.local_explainer import LocalDeterministicExplainer
from app.ai.models import (
    AIExplanationResult,
    DataTransferPreview,
    ExplanationMode,
    PresetQuestionType,
    PRESET_QUESTION_TEXTS,
    SanitizedAIExplanationPayload,
    StructuredAIExplanation,
    UserConsentToken,
)
from app.ai.sanitizer import PayloadSanitizer
from app.ai.validator import ExplanationOutputValidator

__all__ = [
    "LayoutSuggestion",
    "LayoutDiagnosis",
    "BaseLayoutAdvisor",
    "GeminiExplanationService",
    "LocalDeterministicExplainer",
    "AIExplanationResult",
    "DataTransferPreview",
    "ExplanationMode",
    "PresetQuestionType",
    "PRESET_QUESTION_TEXTS",
    "SanitizedAIExplanationPayload",
    "StructuredAIExplanation",
    "UserConsentToken",
    "PayloadSanitizer",
    "ExplanationOutputValidator",
]
