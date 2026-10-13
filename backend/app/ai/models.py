"""Data models, request schemas, and structured response contracts for AI Decision Explanation."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExplanationMode(str, Enum):
    """Execution mode for explanation generation."""

    LOCAL = "local"
    GEMINI = "gemini"


class PresetQuestionType(str, Enum):
    """Standard audit questions supported by the decision explanation system."""

    WHY_STRATEGY_SELECTED = "why_strategy_selected"
    WHY_FEASIBLE = "why_feasible"
    PARETO_COMPARISON = "pareto_comparison"
    SOFT_PENALTY_EXPLANATION = "soft_penalty_explanation"
    FALLBACK_REASON = "fallback_reason"
    GLOBAL_OPTIMALITY_QUERY = "global_optimality_query"
    CUSTOM = "custom"


PRESET_QUESTION_TEXTS = {
    PresetQuestionType.WHY_STRATEGY_SELECTED: "Why did FLODSS select this algorithm?",
    PresetQuestionType.WHY_FEASIBLE: "Why is this factory layout feasible?",
    PresetQuestionType.PARETO_COMPARISON: "What is the difference between these two Pareto alternatives?",
    PresetQuestionType.SOFT_PENALTY_EXPLANATION: "What does the soft constraint penalty mean?",
    PresetQuestionType.FALLBACK_REASON: "Why did the fallback algorithm run?",
    PresetQuestionType.GLOBAL_OPTIMALITY_QUERY: "Is this result guaranteed to be globally optimal?",
}


class SanitizedPayloadDepartment(BaseModel):
    """Whitelisted anonymized department descriptor (strictly excluding coordinates & proprietary names)."""

    dept_alias: str = Field(..., description="Anonymized label, e.g. 'Dept 1'")
    required_area: float = Field(..., description="Required area in m²")
    category: str = Field(default="production", description="Generic functional group")


class SanitizedAIExplanationPayload(BaseModel):
    """Whitelisted data structure permitted to be viewed or transmitted to Gemini API.
    
    CONFIDENTIALITY GUARANTEE:
    - Zero source code
    - Zero git repository metadata
    - Zero raw flow matrix entries (F_ij, C_ij)
    - Zero exact coordinates (x, y, width, height)
    - Zero proprietary department names
    - Zero API keys or system environment variables
    """

    problem_id: str
    facility_dimensions: Dict[str, float] = Field(..., description="Width, height, area")
    department_count: int
    area_utilization_pct: float
    anonymized_departments: List[SanitizedPayloadDepartment] = Field(default_factory=list)
    selected_strategy_name: str
    selected_archetype: str
    primary_algorithm: str
    fallback_triggered: bool
    fallback_reason: Optional[str] = None
    canonical_metrics: Dict[str, float] = Field(..., description="Grounded metrics (MHC, REL%, Soft Penalty)")
    violations_summary: Dict[str, Any] = Field(default_factory=dict)
    pareto_rank: Optional[int] = None
    is_non_dominated: Optional[bool] = None
    alternative_comparison: Optional[Dict[str, Any]] = None
    question_type: str
    question_text: str
    payload_hash: str = Field(..., description="SHA-256 fingerprint over canonical JSON of this payload")


class DataTransferPreview(BaseModel):
    """Transparent preview shown to user before requesting explicit Gemini API consent."""

    provider: str = "Google Gemini API"
    target_model: str
    purpose: str = "Explain optimization results and engineering constraints without exposing coordinates, flows, or source code."
    privacy_impact: str = (
        "This request transmits high-level aggregated metrics and anonymized department areas. "
        "Coordinates, flows, source code, and confidential names are excluded. "
        "Anonymization significantly reduces, but does not completely eliminate, external data transmission risk. "
        "Review the exact payload below before consenting."
    )
    whitelisted_fields: List[str] = Field(default_factory=list)
    excluded_sensitive_fields: List[str] = Field(default_factory=list)
    payload: SanitizedAIExplanationPayload
    payload_hash: str
    consent_token: str = Field(..., description="Cryptographically signed token binding consent to this exact payload")


class UserConsentToken(BaseModel):
    """Signed token validating user permission for a specific payload transmission."""

    payload_hash: str
    granted_at: str
    expires_at: str
    signature: str


class StructuredAIExplanation(BaseModel):
    """Structured response schema enforced on both local and Gemini explanations."""

    summary: str = Field(..., description="Clear, non-technical summary of the decision or metric")
    main_reasons: List[str] = Field(default_factory=list, description="Primary technical rationales")
    strengths: List[str] = Field(default_factory=list, description="Key engineering advantages")
    risks: List[str] = Field(default_factory=list, description="Potential operational or layout risks")
    trade_offs: List[str] = Field(default_factory=list, description="Multi-objective compromises")
    limitations: List[str] = Field(default_factory=list, description="Modeling assumptions and boundaries")
    evidence_references: List[str] = Field(
        default_factory=list,
        description="List of canonical metric IDs cited (e.g. 'material_handling_cost', 'soft_penalty')"
    )
    global_optimality_disclaimer: str = Field(
        default="Facility Layout Problem is strongly NP-hard. FLODSS uses heuristic and metaheuristic algorithms; no mathematical guarantee of global optimality is claimed.",
        description="Mandatory engineering disclaimer regarding heuristic optimality boundaries"
    )


class AIExplanationResult(BaseModel):
    """Complete response returned to user with provenance and verified numerical ground truth."""

    mode: ExplanationMode
    question: str
    explanation: StructuredAIExplanation
    verified_canonical_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Exact verified metrics from CanonicalEvaluationService"
    )
    provenance: Dict[str, Any] = Field(default_factory=dict)
    validation_passed: bool = True
    fallback_to_local_used: bool = False
    fallback_reason: Optional[str] = None


class ExplainLocalRequest(BaseModel):
    """Request schema for offline local deterministic explanation."""

    problem_id: str
    question_type: PresetQuestionType = PresetQuestionType.WHY_STRATEGY_SELECTED
    custom_question: Optional[str] = None
    layout_signature: Optional[str] = None
    comparison_layout_signature: Optional[str] = None


class PreviewPayloadRequest(BaseModel):
    """Request schema to preview the exact data packet before consenting to Gemini."""

    problem_id: str
    question_type: PresetQuestionType = PresetQuestionType.WHY_STRATEGY_SELECTED
    custom_question: Optional[str] = None
    layout_signature: Optional[str] = None
    comparison_layout_signature: Optional[str] = None
    client_session_id: str = Field(default="default_session", description="Client session ID for authorization tracking")


class GrantConsentRequest(BaseModel):
    """Explicit human authorization request to transmit sanitized payload to Gemini."""

    payload_hash: str = Field(..., description="Target payload fingerprint being authorized")
    client_session_id: str = Field(default="default_session", description="Client session granting consent")
    consent_acknowledged: bool = Field(default=True, description="Explicit human acknowledgment checkbox")
    opt_in_exact_dimensions: bool = Field(default=False, description="User opt-in to transmit exact meters")
    opt_in_exact_areas: bool = Field(default=False, description="User opt-in to transmit exact m² areas")
    opt_in_financial_costs: bool = Field(default=False, description="User opt-in to transmit dollar costs")


class GrantConsentResponse(BaseModel):
    """Single-use cryptographically bound authorization response."""

    consent_token: str
    payload_hash: str
    client_session_id: str
    expires_at: str
    single_use: bool = True


class ExplainGeminiRequest(BaseModel):
    """Request schema for Gemini explanation with mandatory user consent token."""

    problem_id: str
    question_type: PresetQuestionType = PresetQuestionType.WHY_STRATEGY_SELECTED
    custom_question: Optional[str] = None
    layout_signature: Optional[str] = None
    comparison_layout_signature: Optional[str] = None
    payload_hash: str = Field(..., description="Hash of the previewed payload")
    consent_token: str = Field(..., description="Cryptographically signed single-use consent token")
    client_session_id: str = Field(default="default_session", description="Client session ID matching authorization")
