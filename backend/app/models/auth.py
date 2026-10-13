"""Authentication and user management models for FLODSS."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User access roles in FLODSS."""
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    VIEWER = "VIEWER"


class User(BaseModel):
    """Complete internal user model."""
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    allow_gemini: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserResponse(BaseModel):
    """Safe public user profile representation."""
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    allow_gemini: bool
    created_at: str


class LoginRequest(BaseModel):
    """Credentials payload for authentication."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Plaintext password")


class LoginResponse(BaseModel):
    """Successful authentication response payload."""
    session_token: str
    user: UserResponse
    expires_at: str


class InvitationCreate(BaseModel):
    """Payload for creating a new user invitation by Admin."""
    email: str = Field(..., description="Target invitee email address")
    role: UserRole = Field(default=UserRole.RESEARCHER, description="Assigned role for new user")


class InvitationResponse(BaseModel):
    """Details of a generated or retrieved user invitation."""
    id: str
    token: str
    email: str
    role: UserRole
    created_by_user_id: str
    created_at: str
    expires_at: str
    used_at: Optional[str] = None
    is_revoked: bool = False


class InvitationAccept(BaseModel):
    """Payload to accept an invitation and initialize user account."""
    token: str = Field(..., description="Invitation token received from administrator")
    full_name: str = Field(..., min_length=2, description="User full display name")
    password: str = Field(..., min_length=8, description="New account password (min 8 characters)")


class UserStatusUpdate(BaseModel):
    """Admin payload to modify user active status, AI privilege, or role."""
    is_active: Optional[bool] = None
    allow_gemini: Optional[bool] = None
    role: Optional[UserRole] = None
