"""FastAPI dependency providers for authentication, authorization, and resource limits."""

import sqlite3
from typing import Callable, Optional
from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.security import concurrency_manager
from app.db.database import get_db
from app.models.auth import User, UserRole
from app.services.auth_service import AuthService


def get_token_from_request(
    authorization: Optional[str] = Header(None),
    flodss_session: Optional[str] = Cookie(None),
) -> Optional[str]:
    """Extract session token from Bearer authorization header or HTTP-only session cookie."""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    if flodss_session:
        return flodss_session.strip()
    return None


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    flodss_session: Optional[str] = Cookie(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> User:
    """Validate active session token and return authenticated User."""
    token = get_token_from_request(authorization, flodss_session)
    if not token:
        if not settings.AUTH_ENFORCED:
            guest_data = AuthService.login_guest_user(conn)
            return guest_data["user"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with a valid research session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = AuthService.get_user_by_session_token(token, conn)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your research account has been disabled. Please contact an administrator.",
        )

    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    flodss_session: Optional[str] = Cookie(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> Optional[User]:
    """Retrieve user if valid session exists; otherwise return None without raising 401."""
    token = get_token_from_request(authorization, flodss_session)
    if not token:
        return None
    return AuthService.get_user_by_session_token(token, conn)


def require_role(*roles: UserRole) -> Callable:
    """Dependency factory checking that current user possesses an authorized role."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            required_names = [r.value for r in roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This operation requires one of the following roles: {required_names}. Current role: '{current_user.role.value}'.",
            )
        return current_user
    return role_checker


class JobSlotGuard:
    """Context guard to enforce and release per-user and system-wide concurrent optimization slots."""

    def __init__(self, user: User):
        self.user_id = user.id

    def __enter__(self):
        total_active = concurrency_manager.get_total_active_count()
        if total_active >= settings.MAX_TOTAL_CONCURRENT_JOBS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"System-wide optimization capacity reached ({settings.MAX_TOTAL_CONCURRENT_JOBS} active jobs). Please retry once running jobs finish.",
            )
        acquired = concurrency_manager.acquire(
            self.user_id,
            max_concurrent=settings.MAX_CONCURRENT_JOBS_PER_USER,
            max_total=settings.MAX_TOTAL_CONCURRENT_JOBS,
        )
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Concurrent job limit exceeded. You may run at most {settings.MAX_CONCURRENT_JOBS_PER_USER} simultaneous optimization processes.",
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        concurrency_manager.release(self.user_id)


def get_job_slot(current_user: User = Depends(get_current_user)):
    """FastAPI dependency yielding current user while holding an active execution slot."""
    with JobSlotGuard(current_user):
        yield current_user
