"""Research project, problem persistence, and experiment isolation models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    VIEW = "VIEW"
    EDIT = "EDIT"
    ADMIN = "ADMIN"


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_user_id: str
    is_archived: bool = False
    created_at: str
    updated_at: str
    problem_count: int = 0
    run_count: int = 0


class AccessGrantCreate(BaseModel):
    user_id: str
    permission: PermissionLevel = PermissionLevel.VIEW


class ProblemRecord(BaseModel):
    id: str
    project_id: str
    name: str
    problem_hash: str
    facility_data: Dict[str, Any]
    owner_user_id: str
    created_at: str
    updated_at: str


class OptimizationRunRecord(BaseModel):
    id: str
    project_id: str
    problem_id: str
    user_id: str
    algorithm_name: str
    algorithm_version: str
    flodss_version: str
    parameters: Dict[str, Any]
    random_seed: int
    status: RunStatus
    termination_reason: Optional[str] = None
    runtime_ms: float
    problem_hash: str
    evaluation_config_hash: str
    layout_signature: Optional[str] = None
    is_feasible: bool
    canonical_metrics: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None


class SaveExperimentRequest(BaseModel):
    project_id: str
    problem_id: str
    algorithm_name: str
    algorithm_version: Optional[str] = "1.0.0"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    random_seed: int = 42
    runtime_ms: float
    termination_reason: Optional[str] = None
    problem_hash: str
    evaluation_config_hash: str
    layout_signature: str
    is_feasible: bool
    canonical_metrics: Dict[str, Any]
    layout_data: Optional[Dict[str, Any]] = None
    evaluation_report: Optional[Dict[str, Any]] = None


class AuditLogRecord(BaseModel):
    id: str
    user_id: Optional[str] = None
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str
