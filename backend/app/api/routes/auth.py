"""Authentication, invitation management, and user governance endpoints."""

import sqlite3
from typing import List
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from app.api.deps import get_current_user, get_token_from_request, require_role
from app.db.database import get_db
from app.models.auth import (
    InvitationAccept,
    InvitationCreate,
    InvitationResponse,
    LoginRequest,
    LoginResponse,
    User,
    UserResponse,
    UserRole,
    UserStatusUpdate,
)
from app.core.config import settings
from app.core.security import get_trusted_client_ip, is_trusted_secure_request
from app.services.auth_service import AuthService
from app.services.cloudflare_access_service import CloudflareAccessError, CloudflareAccessService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """Resolve client IP address with proxy header anti-spoofing protection."""
    return get_trusted_client_ip(request)


def _should_use_secure_cookie(request: Request) -> bool:
    """Determine whether session cookies must have the Secure flag via trusted connection."""
    return is_trusted_secure_request(request)


@router.post("/login", response_model=LoginResponse, summary="Authenticate Research User")
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> LoginResponse:
    """Authenticate with email and password, issuing a signed session token."""
    if settings.effective_perimeter_mode == "MANAGED_ACCESS":
        # Mode A: Full Enterprise Zero Trust with cryptographic RS256 JWKS JWT assertion
        try:
            cf_payload = CloudflareAccessService.extract_and_verify_request(request)
        except CloudflareAccessError as cae:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(cae),
            )

        if not cf_payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cloudflare perimeter authentication required.",
            )

        verified_email = (cf_payload.get("email") or cf_payload.get("sub", "")).strip().lower()
        if req.email.strip().lower() != verified_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Login email ({req.email}) must match cryptographically verified Cloudflare Access email ({verified_email}).",
            )
    elif settings.effective_perimeter_mode == "PROTECTED_QUICK_TUNNEL":
        # Mode B: Protected Quick Tunnel (--allowed-mail)
        # Anti-spoofing socket check is enforced (request must arrive via trusted local proxy 127.0.0.1).
        # Cloudflare email header is NOT required, NOT trusted as proof of identity, and NEVER bypasses FLODSS auth.
        try:
            CloudflareAccessService.extract_and_verify_request(request)
        except CloudflareAccessError as cae:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(cae),
            )

    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    try:
        auth_data = AuthService.authenticate_user(
            email=req.email,
            password=req.password,
            conn=conn,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ve))

    # Set HTTP-only secure cookie
    response.set_cookie(
        key="flodss_session",
        value=auth_data["session_token"],
        httponly=True,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
        max_age=86400,
    )

    return LoginResponse(
        session_token=auth_data["session_token"],
        user=auth_data["user"],
        expires_at=auth_data["expires_at"],
    )


@router.post("/demo-login", response_model=LoginResponse, summary="One-Click Guest Researcher Demo Login")
def demo_login(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> LoginResponse:
    """Authenticate immediately as a guest researcher without requiring a password or invitation token."""
    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    auth_data = AuthService.login_guest_user(
        conn=conn,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    response.set_cookie(
        key="flodss_session",
        value=auth_data["session_token"],
        httponly=True,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
        max_age=86400,
    )

    return LoginResponse(
        session_token=auth_data["session_token"],
        user=auth_data["user"],
        expires_at=auth_data["expires_at"],
    )


@router.post("/logout", summary="Terminate Active Session")
def logout(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Revoke session token and clear authentication cookie."""
    token = get_token_from_request(
        authorization=request.headers.get("authorization"),
        flodss_session=request.cookies.get("flodss_session"),
    )
    if token:
        AuthService.logout_session(token, conn)
        AuthService.record_audit_event(
            user_id=current_user.id,
            event_type="LOGOUT",
            conn=conn,
        )

    response.delete_cookie(
        key="flodss_session",
        httponly=True,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
    )
    return {"message": "Session terminated successfully."}


@router.get("/me", response_model=UserResponse, summary="Get Current Authenticated Profile")
def get_current_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve verified profile of currently logged-in researcher or administrator."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        allow_gemini=current_user.allow_gemini,
        created_at=current_user.created_at,
    )


# --- Invitation Management (Admin) ---


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate User Invitation (Admin)",
)
def create_invitation(
    req: InvitationCreate,
    conn: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> InvitationResponse:
    """Generate an expiring, single-use invitation token for a new researcher or viewer."""
    return AuthService.create_invitation(
        created_by_user_id=admin.id,
        email=req.email,
        role=req.role,
        conn=conn,
    )


@router.get(
    "/invitations",
    response_model=List[InvitationResponse],
    summary="List All Generated Invitations (Admin)",
)
def list_invitations(
    conn: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> List[InvitationResponse]:
    """Inspect history and status of all invitation tokens."""
    return AuthService.list_invitations(conn)


# --- Public Invitation Acceptance ---


@router.get(
    "/invitations/{token}",
    response_model=InvitationResponse,
    summary="Verify Invitation Validity (Public)",
)
def verify_invitation(
    token: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> InvitationResponse:
    """Check whether an invitation token is valid, unexpired, and unconsumed."""
    inv = AuthService.get_invitation_by_token(token, conn)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token is invalid, expired, or has already been used.",
        )
    return inv


@router.post(
    "/invitations/accept",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept Invitation & Register Account (Public)",
)
def accept_invitation(
    req: InvitationAccept,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> LoginResponse:
    """Register account using a valid invitation token and initiate first session."""
    if settings.effective_perimeter_mode == "MANAGED_ACCESS":
        # Mode A: Full Enterprise Zero Trust with cryptographic RS256 JWKS JWT assertion
        try:
            cf_payload = CloudflareAccessService.extract_and_verify_request(request)
        except CloudflareAccessError as cae:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(cae),
            )

        if not cf_payload:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cloudflare perimeter authentication required.",
            )

        verified_email = (cf_payload.get("email") or cf_payload.get("sub", "")).strip().lower()
        inv = AuthService.get_invitation_by_token(req.token, conn)
        if not inv or inv.email.strip().lower() != verified_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invitation target email ({inv.email if inv else 'unknown'}) must match cryptographically verified Cloudflare Access email ({verified_email}).",
            )
    elif settings.effective_perimeter_mode == "PROTECTED_QUICK_TUNNEL":
        # Mode B: Protected Quick Tunnel (--allowed-mail)
        # Anti-spoofing socket check is enforced; invitation token and user registration strictly handled by FLODSS.
        try:
            CloudflareAccessService.extract_and_verify_request(request)
        except CloudflareAccessError as cae:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(cae),
            )

    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    try:
        auth_data = AuthService.accept_invitation(
            token=req.token,
            full_name=req.full_name,
            password=req.password,
            conn=conn,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    response.set_cookie(
        key="flodss_session",
        value=auth_data["session_token"],
        httponly=True,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
        max_age=86400,
    )

    return LoginResponse(
        session_token=auth_data["session_token"],
        user=auth_data["user"],
        expires_at=auth_data["expires_at"],
    )


# --- User Governance (Admin) ---


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List Registered Research Users (Admin)",
)
def list_users(
    conn: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> List[UserResponse]:
    """Retrieve full catalog of active and disabled research accounts."""
    return AuthService.list_users(conn)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Modify User Status & AI Privileges (Admin)",
)
def update_user_status(
    user_id: str,
    update: UserStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    """Enable/disable user accounts or toggle Gemini AI access privileges."""
    try:
        return AuthService.update_user_status(
            user_id=user_id,
            update=update,
            admin_user_id=admin.id,
            conn=conn,
        )
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
