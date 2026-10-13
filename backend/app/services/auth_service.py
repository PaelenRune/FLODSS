"""Authentication, user governance, and security audit service."""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.security import (
    generate_secure_token,
    hash_password,
    hash_token,
    rate_limiter,
    verify_password,
)
from app.models.auth import (
    InvitationResponse,
    User,
    UserResponse,
    UserRole,
    UserStatusUpdate,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuthService:
    """Core identity, session, and invitation management service."""

    @staticmethod
    def ensure_admin_user(conn: sqlite3.Connection):
        """Seed initial administrator if no admin user exists."""
        cursor = conn.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1;")
        if cursor.fetchone() is None:
            admin_id = str(uuid.uuid4())
            hashed = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
            now = _now_iso()
            conn.execute(
                """
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ADMIN', 1, 1, ?, ?);
                """,
                (
                    admin_id,
                    settings.DEFAULT_ADMIN_EMAIL.lower(),
                    hashed,
                    settings.DEFAULT_ADMIN_NAME,
                    now,
                    now,
                ),
            )
            conn.commit()

    @staticmethod
    def create_invitation(
        created_by_user_id: str,
        email: str,
        role: UserRole,
        conn: sqlite3.Connection,
    ) -> InvitationResponse:
        """Create a single-use expiring invitation token."""
        inv_id = str(uuid.uuid4())
        token = generate_secure_token(32)
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=settings.INVITATION_EXPIRE_HOURS)).isoformat()
        now_str = now.isoformat()

        conn.execute(
            """
            INSERT INTO invitations (id, token, email, role, created_by_user_id, created_at, expires_at, is_revoked)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0);
            """,
            (
                inv_id,
                token,
                email.strip().lower(),
                role.value,
                created_by_user_id,
                now_str,
                expires_at,
            ),
        )
        conn.commit()

        AuthService.record_audit_event(
            user_id=created_by_user_id,
            event_type="INVITATION_CREATED",
            resource_type="invitation",
            resource_id=inv_id,
            details={"email": email, "role": role.value},
            conn=conn,
        )

        return InvitationResponse(
            id=inv_id,
            token=token,
            email=email.strip().lower(),
            role=role,
            created_by_user_id=created_by_user_id,
            created_at=now_str,
            expires_at=expires_at,
            is_revoked=False,
        )

    @staticmethod
    def get_invitation_by_token(token: str, conn: sqlite3.Connection) -> Optional[InvitationResponse]:
        """Verify invitation token status and return details if valid and unexpired."""
        cursor = conn.execute(
            """
            SELECT id, token, email, role, created_by_user_id, created_at, expires_at, used_at, is_revoked
            FROM invitations
            WHERE token = ?;
            """,
            (token,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Check expiration
        now = datetime.now(timezone.utc).isoformat()
        if row["is_revoked"] or row["used_at"] is not None or now > row["expires_at"]:
            return None

        return InvitationResponse(
            id=row["id"],
            token=row["token"],
            email=row["email"],
            role=UserRole(row["role"]),
            created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            used_at=row["used_at"],
            is_revoked=bool(row["is_revoked"]),
        )

    @staticmethod
    def accept_invitation(
        token: str,
        full_name: str,
        password: str,
        conn: sqlite3.Connection,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Accept invitation, provision user account, and issue session token."""
        inv = AuthService.get_invitation_by_token(token, conn)
        if not inv:
            raise ValueError("Invitation token is invalid, expired, or has already been used.")

        # Check if email is already registered
        cursor = conn.execute("SELECT id FROM users WHERE email = ?;", (inv.email,))
        if cursor.fetchone() is not None:
            raise ValueError(f"An account with email '{inv.email}' already exists.")

        user_id = str(uuid.uuid4())
        hashed = hash_password(password)
        now_str = _now_iso()

        # Insert user
        conn.execute(
            """
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?);
            """,
            (user_id, inv.email, hashed, full_name.strip(), inv.role.value, now_str, now_str),
        )

        # Mark invitation used
        conn.execute(
            "UPDATE invitations SET used_at = ? WHERE id = ?;",
            (now_str, inv.id),
        )

        # Create initial default project for researcher
        proj_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO research_projects (id, name, description, owner_user_id, is_archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?);
            """,
            (
                proj_id,
                f"{full_name.strip()}'s Research Workspace",
                "Default research project initialized upon onboarding.",
                user_id,
                now_str,
                now_str,
            ),
        )

        # Issue session
        session_token = generate_secure_token(32)
        token_hashed = hash_token(session_token)
        session_id = str(uuid.uuid4())
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_EXPIRE_HOURS)).isoformat()

        conn.execute(
            """
            INSERT INTO sessions (id, token_hash, user_id, created_at, expires_at, is_revoked, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?);
            """,
            (session_id, token_hashed, user_id, now_str, expires_at, ip_address, user_agent),
        )
        conn.commit()

        AuthService.record_audit_event(
            user_id=user_id,
            event_type="INVITATION_ACCEPTED",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip_address,
            details={"email": inv.email, "role": inv.role.value},
            conn=conn,
        )

        user_obj = UserResponse(
            id=user_id,
            email=inv.email,
            full_name=full_name.strip(),
            role=inv.role,
            is_active=True,
            allow_gemini=False,
            created_at=now_str,
        )

        return {
            "session_token": session_token,
            "user": user_obj,
            "expires_at": expires_at,
        }

    @staticmethod
    def authenticate_user(
        email: str,
        password: str,
        conn: sqlite3.Connection,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authenticate user credentials, enforce rate limits, and issue session."""
        rate_key = ip_address or email.strip().lower()
        if not rate_limiter.is_allowed(
            rate_key,
            settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
            settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
        ):
            AuthService.record_audit_event(
                user_id=None,
                event_type="LOGIN_RATE_LIMITED",
                ip_address=ip_address,
                details={"email": email},
                conn=conn,
            )
            raise PermissionError("Too many failed login attempts. Please wait 5 minutes before retrying.")

        cursor = conn.execute(
            """
            SELECT id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at
            FROM users
            WHERE email = ?;
            """,
            (email.strip().lower(),),
        )
        row = cursor.fetchone()

        if not row or not verify_password(password, row["hashed_password"]):
            rate_limiter.record_attempt(rate_key)
            AuthService.record_audit_event(
                user_id=row["id"] if row else None,
                event_type="LOGIN_FAILED",
                ip_address=ip_address,
                details={"email": email},
                conn=conn,
            )
            raise ValueError("Invalid email or password.")

        if not bool(row["is_active"]):
            AuthService.record_audit_event(
                user_id=row["id"],
                event_type="LOGIN_BLOCKED_DISABLED",
                ip_address=ip_address,
                conn=conn,
            )
            raise PermissionError("Account has been disabled by an administrator. Please contact your lab supervisor.")

        # Successful login: reset rate limit attempts
        rate_limiter.reset(rate_key)

        session_token = generate_secure_token(32)
        token_hashed = hash_token(session_token)
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=settings.SESSION_EXPIRE_HOURS)).isoformat()
        now_str = now.isoformat()

        conn.execute(
            """
            INSERT INTO sessions (id, token_hash, user_id, created_at, expires_at, is_revoked, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?);
            """,
            (session_id, token_hashed, row["id"], now_str, expires_at, ip_address, user_agent),
        )
        conn.commit()

        AuthService.record_audit_event(
            user_id=row["id"],
            event_type="LOGIN_SUCCESS",
            ip_address=ip_address,
            conn=conn,
        )

        user_obj = UserResponse(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            allow_gemini=bool(row["allow_gemini"]),
            created_at=row["created_at"],
        )

        return {
            "session_token": session_token,
            "user": user_obj,
            "expires_at": expires_at,
        }

    @staticmethod
    def login_guest_user(
        conn: sqlite3.Connection,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or retrieve a guest researcher account and issue a valid session."""
        guest_email = "guest@flodss.local"
        cursor = conn.execute(
            """
            SELECT id, email, full_name, role, is_active, allow_gemini, created_at
            FROM users
            WHERE email = ?;
            """,
            (guest_email,),
        )
        row = cursor.fetchone()
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        if row is None:
            user_id = str(uuid.uuid4())
            dummy_hash = hash_password(generate_secure_token(32))
            full_name = "Misafir Araştırmacı (Demo)"
            conn.execute(
                """
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'RESEARCHER', 1, 1, ?, ?);
                """,
                (user_id, guest_email, dummy_hash, full_name, now_str, now_str),
            )
            conn.commit()
            user_role = UserRole.RESEARCHER
            allow_gemini = True
            created_at = now_str
        else:
            user_id = row["id"]
            user_role = UserRole(row["role"])
            full_name = row["full_name"]
            allow_gemini = bool(row["allow_gemini"])
            created_at = row["created_at"]
            if not row["is_active"]:
                conn.execute("UPDATE users SET is_active = 1, updated_at = ? WHERE id = ?;", (now_str, user_id))
                conn.commit()

        # Ensure guest has at least one research project ready
        proj_cur = conn.execute("SELECT id FROM research_projects WHERE owner_user_id = ? LIMIT 1;", (user_id,))
        if proj_cur.fetchone() is None:
            proj_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO research_projects (id, name, description, owner_user_id, is_archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?);
                """,
                (
                    proj_id,
                    "Pilot Demo Projesi",
                    "Misafir araştırmacı deneme ve tesis yerleşim optimizasyon çalışma alanı",
                    user_id,
                    now_str,
                    now_str,
                ),
            )
            conn.commit()

        session_token = generate_secure_token(32)
        token_hashed = hash_token(session_token)
        session_id = str(uuid.uuid4())
        expires_at = (now + timedelta(hours=settings.SESSION_EXPIRE_HOURS)).isoformat()

        conn.execute(
            """
            INSERT INTO sessions (id, token_hash, user_id, created_at, expires_at, is_revoked, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?);
            """,
            (session_id, token_hashed, user_id, now_str, expires_at, ip_address, user_agent),
        )
        conn.commit()

        AuthService.record_audit_event(
            user_id=user_id,
            event_type="DEMO_LOGIN_SUCCESS",
            ip_address=ip_address,
            conn=conn,
        )

        user_obj = UserResponse(
            id=user_id,
            email=guest_email,
            full_name=full_name,
            role=user_role,
            is_active=True,
            allow_gemini=allow_gemini,
            created_at=created_at,
        )

        return {
            "session_token": session_token,
            "user": user_obj,
            "expires_at": expires_at,
        }

    @staticmethod
    def get_user_by_session_token(token: str, conn: sqlite3.Connection) -> Optional[User]:
        """Validate session token and return active user profile."""
        token_hashed = hash_token(token)
        now_str = _now_iso()

        cursor = conn.execute(
            """
            SELECT s.id as session_id, s.expires_at, s.is_revoked,
                   u.id, u.email, u.full_name, u.role, u.is_active, u.allow_gemini, u.created_at, u.updated_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token_hash = ?;
            """,
            (token_hashed,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Check session validity
        if row["is_revoked"] or now_str > row["expires_at"]:
            return None

        # Check user active status
        if not bool(row["is_active"]):
            return None

        return User(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            allow_gemini=bool(row["allow_gemini"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def get_user_by_email(email: str, conn: sqlite3.Connection) -> Optional[User]:
        """Fetch user by email address."""
        cursor = conn.execute(
            """
            SELECT id, email, full_name, role, is_active, allow_gemini, created_at, updated_at
            FROM users
            WHERE email = ?;
            """,
            (email.strip().lower(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            allow_gemini=bool(row["allow_gemini"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def logout_session(token: str, conn: sqlite3.Connection):
        """Revoke active session token in database."""
        token_hashed = hash_token(token)
        conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token_hash = ?;", (token_hashed,))
        conn.commit()

    @staticmethod
    def list_users(conn: sqlite3.Connection) -> List[UserResponse]:
        """Retrieve all registered users (Admin only)."""
        cursor = conn.execute(
            """
            SELECT id, email, full_name, role, is_active, allow_gemini, created_at
            FROM users
            ORDER BY created_at ASC;
            """
        )
        return [
            UserResponse(
                id=r["id"],
                email=r["email"],
                full_name=r["full_name"],
                role=UserRole(r["role"]),
                is_active=bool(r["is_active"]),
                allow_gemini=bool(r["allow_gemini"]),
                created_at=r["created_at"],
            )
            for r in cursor.fetchall()
        ]

    @staticmethod
    def list_invitations(conn: sqlite3.Connection) -> List[InvitationResponse]:
        """Retrieve all invitations (Admin only)."""
        cursor = conn.execute(
            """
            SELECT id, token, email, role, created_by_user_id, created_at, expires_at, used_at, is_revoked
            FROM invitations
            ORDER BY created_at DESC;
            """
        )
        return [
            InvitationResponse(
                id=r["id"],
                token=r["token"],
                email=r["email"],
                role=UserRole(r["role"]),
                created_by_user_id=r["created_by_user_id"],
                created_at=r["created_at"],
                expires_at=r["expires_at"],
                used_at=r["used_at"],
                is_revoked=bool(r["is_revoked"]),
            )
            for r in cursor.fetchall()
        ]

    @staticmethod
    def update_user_status(
        user_id: str,
        update: UserStatusUpdate,
        admin_user_id: str,
        conn: sqlite3.Connection,
    ) -> UserResponse:
        """Update user active state, role, or Gemini privilege."""
        cursor = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise KeyError(f"User '{user_id}' not found.")

        is_active = update.is_active if update.is_active is not None else bool(row["is_active"])
        allow_gemini = update.allow_gemini if update.allow_gemini is not None else bool(row["allow_gemini"])
        role = update.role.value if update.role is not None else row["role"]
        now_str = _now_iso()

        conn.execute(
            """
            UPDATE users
            SET is_active = ?, allow_gemini = ?, role = ?, updated_at = ?
            WHERE id = ?;
            """,
            (int(is_active), int(allow_gemini), role, now_str, user_id),
        )

        # If disabling account, revoke all sessions
        if not is_active:
            conn.execute("UPDATE sessions SET is_revoked = 1 WHERE user_id = ?;", (user_id,))

        conn.commit()

        AuthService.record_audit_event(
            user_id=admin_user_id,
            event_type="USER_STATUS_UPDATED",
            resource_type="user",
            resource_id=user_id,
            details={
                "is_active": is_active,
                "allow_gemini": allow_gemini,
                "role": role,
            },
            conn=conn,
        )

        return UserResponse(
            id=user_id,
            email=row["email"],
            full_name=row["full_name"],
            role=UserRole(role),
            is_active=is_active,
            allow_gemini=allow_gemini,
            created_at=row["created_at"],
        )

    @staticmethod
    def record_audit_event(
        user_id: Optional[str],
        event_type: str,
        conn: sqlite3.Connection,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Append an immutable audit entry."""
        event_id = str(uuid.uuid4())
        now_str = _now_iso()
        details_json = json.dumps(details) if details else None
        conn.execute(
            """
            INSERT INTO audit_events (id, user_id, event_type, resource_type, resource_id, ip_address, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                event_id,
                user_id,
                event_type,
                resource_type,
                resource_id,
                ip_address,
                details_json,
                now_str,
            ),
        )
        conn.commit()
