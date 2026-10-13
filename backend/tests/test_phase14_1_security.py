"""Tests for Phase 14.1: Controlled Research Access, Multi-Tenant Isolation, Authentication & Authorization."""

import json
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    RateLimiter,
    JobConcurrencyManager,
    hash_password,
    verify_password,
    generate_secure_token,
    hash_token,
)
from app.db.database import db_manager
from app.models.auth import User, UserRole, UserStatusUpdate
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService


@pytest.fixture
def clean_client():
    """Client without auth override to test authentic HTTP authentication."""
    app.dependency_overrides.clear()
    c = TestClient(app)
    yield c


def _insert_user(user_id: str, email: str, full_name: str, role: str) -> User:
    """Helper to insert real user into SQLite database so foreign key constraints are satisfied."""
    now = "2026-10-12T00:00:00Z"
    with db_manager.get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
            VALUES (?, ?, 'mock_hash', ?, ?, 1, 0, ?, ?);
            """,
            (user_id, email, full_name, role, now, now),
        )
        conn.commit()
    return User(
        id=user_id,
        email=email,
        full_name=full_name,
        role=UserRole(role),
        is_active=True,
        allow_gemini=False,
        created_at=now,
        updated_at=now,
    )


class TestSecurityPrimitives:
    """Verify core cryptographic functions, token generators, rate limiters, and concurrency managers."""

    def test_password_hashing_and_verification(self):
        secret = "ResearchSecurePass2026!"
        hashed = hash_password(secret)
        assert hashed.startswith("pbkdf2_sha256$600000$")
        assert verify_password(secret, hashed) is True
        assert verify_password("WrongPass123", hashed) is False

    def test_token_generation_and_hashing(self):
        token = generate_secure_token(32)
        assert len(token) > 40
        h1 = hash_token(token)
        h2 = hash_token(token)
        assert h1 == h2
        assert len(h1) == 64

    def test_rate_limiter_sliding_window(self):
        limiter = RateLimiter()
        key = "test_user_rate_limit"
        # 5 allowed attempts
        for _ in range(5):
            assert limiter.is_allowed(key, max_attempts=5, window_seconds=60) is True
            limiter.record_attempt(key)
        # 6th attempt must be rejected
        assert limiter.is_allowed(key, max_attempts=5, window_seconds=60) is False
        # Reset
        limiter.reset(key)
        assert limiter.is_allowed(key, max_attempts=5, window_seconds=60) is True

    def test_job_concurrency_manager(self):
        mgr = JobConcurrencyManager()
        uid = "usr_concurrent_test"
        assert mgr.acquire(uid, max_concurrent=2) is True
        assert mgr.acquire(uid, max_concurrent=2) is True
        # 3rd simultaneous job must be rejected
        assert mgr.acquire(uid, max_concurrent=2) is False
        # Release one slot
        mgr.release(uid)
        assert mgr.acquire(uid, max_concurrent=2) is True


class TestAuthenticationAndAuthorizationEnforcement:
    """Verify anonymous access restrictions, role hierarchy, and login authentication."""

    def test_anonymous_access_denied_on_sensitive_routes(self, clean_client):
        # Protected endpoints must reject unauthenticated requests with 401
        res = clean_client.get("/api/problems/examples")
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

        res = clean_client.get("/api/projects")
        assert res.status_code == 401

        res = clean_client.get("/api/algorithms")
        assert res.status_code == 401

        res = clean_client.get("/api/benchmarks/latest")
        assert res.status_code == 401

        res = clean_client.get("/api/ai/status")
        assert res.status_code == 401

    def test_public_routes_remain_accessible(self, clean_client):
        # Root and health must be open
        res = clean_client.get("/")
        assert res.status_code == 200

        res = clean_client.get("/api/health")
        assert res.status_code == 200

    def test_admin_login_and_session_cookie(self, clean_client):
        res = clean_client.post(
            "/api/auth/login",
            json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
        )
        assert res.status_code == 200
        data = res.json()
        assert "session_token" in data
        assert data["user"]["email"] == "admin@flodss.local"
        assert data["user"]["role"] == "ADMIN"
        # Verify flodss_session cookie
        assert "flodss_session" in res.cookies

    def test_invalid_login_rejection(self, clean_client):
        res = clean_client.post(
            "/api/auth/login",
            json={"email": "admin@flodss.local", "password": "WrongPassword!"},
        )
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["detail"]


class TestRoleHierarchyAndPrivilegeEscalation:
    """Verify VIEWER and RESEARCHER cannot execute unauthorized administrative operations."""

    def test_non_admin_cannot_create_invitations(self):
        researcher = _insert_user("usr_res_role", "res_role@flodss.local", "Dr. Researcher", "RESEARCHER")
        app.dependency_overrides[get_current_user] = lambda: researcher
        c = TestClient(app)

        # Attempt to issue invitation (ADMIN only)
        res = c.post(
            "/api/auth/invitations",
            json={"email": "colleague@flodss.local", "role": "RESEARCHER"},
        )
        assert res.status_code == 403
        assert "requires one of the following roles" in res.json()["detail"]

        # Attempt to view user list (ADMIN only)
        res = c.get("/api/auth/users")
        assert res.status_code == 403

    def test_viewer_cannot_create_projects(self):
        viewer = _insert_user("usr_view_role", "viewer@flodss.local", "Advisor Viewer", "VIEWER")
        app.dependency_overrides[get_current_user] = lambda: viewer
        c = TestClient(app)

        res = c.post("/api/projects", json={"name": "Unauthorized Project", "description": "Test"})
        assert res.status_code == 403
        assert "requires one of the following roles" in res.json()["detail"]


class TestInvitationLifecycle:
    """Verify single-use token lifecycle, expiration, and user account creation."""

    def test_invitation_creation_and_acceptance(self):
        # Retrieve actual seeded admin
        with db_manager.get_connection() as conn:
            admin_user = AuthService.get_user_by_email("admin@flodss.local", conn)
            assert admin_user is not None

        app.dependency_overrides[get_current_user] = lambda: admin_user
        c = TestClient(app)

        # 1. Admin creates invitation for new researcher
        invite_email = f"invited_{int(time.time())}@flodss.local"
        res = c.post(
            "/api/auth/invitations",
            json={"email": invite_email, "role": "RESEARCHER", "full_name": "New Researcher"},
        )
        assert res.status_code == 201
        inv_data = res.json()
        token = inv_data["token"]

        # 2. Inspect invitation anonymously
        app.dependency_overrides.clear()
        c_anon = TestClient(app)
        res = c_anon.get(f"/api/auth/invitations/{token}")
        assert res.status_code == 200
        assert res.json()["email"] == invite_email

        # 3. Accept invitation
        res = c_anon.post(
            "/api/auth/invitations/accept",
            json={
                "token": token,
                "password": "ValidPassword2026!",
                "full_name": "New Researcher, Ph.D.",
            },
        )
        assert res.status_code == 201
        reg_data = res.json()
        assert reg_data["user"]["email"] == invite_email
        assert reg_data["user"]["role"] == "RESEARCHER"

        # 4. Attempt to RE-USE the same invitation token (must fail with 400)
        res_reuse = c_anon.post(
            "/api/auth/invitations/accept",
            json={
                "token": token,
                "password": "AnotherPassword2026!",
                "full_name": "Another Person",
            },
        )
        assert res_reuse.status_code == 400
        assert "already been used" in res_reuse.json()["detail"]


class TestDataIsolationAndIDORProtection:
    """Verify multi-tenant research projects, problem instances, and experiment isolation."""

    def test_idor_cross_user_project_and_experiment_rejection(self):
        user_a = _insert_user("usr_tenant_a", "tenant_a@flodss.local", "Researcher A", "RESEARCHER")
        user_b = _insert_user("usr_tenant_b", "tenant_b@flodss.local", "Researcher B", "RESEARCHER")

        # 1. User A creates a research project
        app.dependency_overrides[get_current_user] = lambda: user_a
        c_a = TestClient(app)
        res = c_a.post("/api/projects", json={"name": "Project Alpha Secret", "description": "Proprietary FLP"})
        assert res.status_code == 201
        proj_a_id = res.json()["id"]

        # 2. User A saves a problem to Project A
        problem_payload = {
            "name": "Classified Factory 10",
            "facility_data": {"id": "FLP_SECRET_10", "width": 100, "height": 60},
        }
        res = c_a.post(f"/api/projects/{proj_a_id}/problems", json=problem_payload)
        assert res.status_code == 201

        # 3. User A saves an experiment run
        exp_payload = {
            "project_id": proj_a_id,
            "problem_id": "FLP_SECRET_10",
            "algorithm_name": "GeneticLayoutAlgorithm",
            "runtime_ms": 1250.0,
            "problem_hash": "hash_secret_10",
            "evaluation_config_hash": "config_hash_1",
            "layout_signature": "sig_secret_10",
            "is_feasible": True,
            "canonical_metrics": {"material_handling_cost": 108504.20},
        }
        res = c_a.post(f"/api/projects/{proj_a_id}/experiments", json=exp_payload)
        assert res.status_code == 201
        run_id = res.json()["id"]

        # 4. User B attempts to access User A's project (BOLA/IDOR attempt)
        app.dependency_overrides[get_current_user] = lambda: user_b
        c_b = TestClient(app)

        # Access project metadata
        res = c_b.get(f"/api/projects/{proj_a_id}")
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]

        # List problems of Project A
        res = c_b.get(f"/api/projects/{proj_a_id}/problems")
        assert res.status_code == 403

        # List runs of Project A
        res = c_b.get(f"/api/projects/{proj_a_id}/experiments")
        assert res.status_code == 403

        # Access specific experiment run
        res = c_b.get(f"/api/experiments/{run_id}")
        assert res.status_code == 403


class TestAccountDisablingAndSessionRevocation:
    """Verify immediate revocation of active sessions when an account is disabled."""

    def test_account_disabling_revokes_sessions(self):
        with db_manager.get_connection() as conn:
            # Create a target user
            u_id = "usr_to_disable"
            now = "2026-10-12T00:00:00Z"
            conn.execute(
                """
                INSERT OR REPLACE INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
                VALUES (?, 'target@flodss.local', 'fakehash', 'Target User', 'RESEARCHER', 1, 0, ?, ?);
                """,
                (u_id, now, now),
            )
            # Create an active session
            token = "session_token_to_revoke"
            t_hash = hash_token(token)
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at, is_revoked)
                VALUES ('sess_target', ?, ?, '2099-01-01T00:00:00Z', ?, 0);
                """,
                (u_id, t_hash, now),
            )
            conn.commit()

            # Confirm session is valid before disabling
            user = AuthService.get_user_by_session_token(token, conn)
            assert user is not None
            assert user.id == u_id

            # Admin disables the account
            AuthService.update_user_status(u_id, UserStatusUpdate(is_active=False), "usr_admin", conn=conn)

            # Confirm session was deleted/revoked
            user_after = AuthService.get_user_by_session_token(token, conn)
            assert user_after is None


class TestSecurityHardeningHeadersAndPayloadLimits:
    """Verify HTTP security response headers and payload size boundaries."""

    def test_security_headers_present(self, clean_client):
        res = clean_client.get("/api/health")
        assert res.status_code == 200
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_payload_too_large_rejection_413(self, clean_client):
        # 11 MB request content-length header
        res = clean_client.post(
            "/api/auth/login",
            headers={"Content-Length": str(11 * 1024 * 1024)},
            json={"email": "admin@flodss.local", "password": "password"},
        )
        assert res.status_code == 413
        assert "Payload Too Large" in res.json()["detail"]
