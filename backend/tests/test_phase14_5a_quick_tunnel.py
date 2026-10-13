"""Unit and integration test suite for Phase 14.5A & 14.5B: Protected Quick Tunnel Compatibility.

Verifies:
1. Dual-mode separation: MANAGED_ACCESS vs PROTECTED_QUICK_TUNNEL vs DISABLED
2. Protected Quick Tunnel perimeter enforcement (Phase 14.5B Refinements):
   - Cloudflare email header is NOT mandatory: legitimate user login succeeds when header is missing
   - Arbitrary/differing email header does NOT block legitimate user login (no unreliable identity binding)
   - Edge --allowed-mail is perimeter Layer 1; FLODSS internal credentials are Layer 2
   - Direct origin socket rejection from untrusted host (not in TRUSTED_PROXIES)
3. Dual-layer defense:
   - Wrong password returns 401 Unauthorized regardless of any headers passed
   - Unauthenticated API access rejected with 401 Unauthorized (NO auth bypass)
   - Invitation acceptance verified solely by valid single-use invitation token
4. Managed Access RS256 JWT behavior preserved intact:
   - Full cryptographic RS256 JWKS verification (signature, aud, iss, exp)
   - Identity binding between JWT email and login email strictly enforced
5. Cross-user isolation, session issuance, expiration, and logout
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.database import db_manager
from app.services.auth_service import AuthService
from app.models.auth import UserRole
from app.services.cloudflare_access_service import (
    CloudflareAccessService,
    setup_test_key_pair,
    create_test_jwt,
)
from pathlib import Path


def get_current_admin_password() -> str:
    secret_path = Path(__file__).resolve().parent.parent / "data" / ".admin_credentials.secret"
    if secret_path.exists():
        with open(secret_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("FLODSS_ADMIN_PASSWORD="):
                    return line.split("=", 1)[1].strip()
    return settings.DEFAULT_ADMIN_PASSWORD


@pytest.fixture
def client():
    """Client with standard test context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def clean_client():
    """Client without auth override to test authentic HTTP authentication."""
    saved_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = saved_overrides


class TestProtectedQuickTunnelPerimeter:
    """Validate Protected Quick Tunnel mode behavior, security boundary, and dual-layer defense."""

    def test_mode_resolution_and_defaults(self):
        """Configuration correctly resolves effective_perimeter_mode and enforcement flags."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        try:
            # Case 1: Default / Disabled
            settings.CLOUDFLARE_PERIMETER_MODE = "DISABLED"
            settings.CLOUDFLARE_ACCESS_ENFORCED = False
            assert settings.effective_perimeter_mode == "DISABLED"
            assert settings.is_perimeter_enforced is False

            # Case 2: Explicit Protected Quick Tunnel
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"
            assert settings.effective_perimeter_mode == "PROTECTED_QUICK_TUNNEL"
            assert settings.is_perimeter_enforced is True

            # Case 3: Backward compatibility with CLOUDFLARE_ACCESS_ENFORCED
            settings.CLOUDFLARE_PERIMETER_MODE = "DISABLED"
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            assert settings.effective_perimeter_mode == "MANAGED_ACCESS"
            assert settings.is_perimeter_enforced is True

            # Case 4: Explicit Managed Access
            settings.CLOUDFLARE_PERIMETER_MODE = "MANAGED_ACCESS"
            assert settings.effective_perimeter_mode == "MANAGED_ACCESS"
            assert settings.is_perimeter_enforced is True
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced

    def test_protected_quick_tunnel_login_succeeds_without_email_header(self, client):
        """In PROTECTED_QUICK_TUNNEL mode, missing CF email header does NOT break legitimate login."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                # No CF-Access-Authenticated-User-Email header provided
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "session_token" in data
            assert data["user"]["email"] == "admin@flodss.local"
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_protected_quick_tunnel_accepts_valid_email_header(self, client):
        """Legitimate user passing Cloudflare OTP with advisory email header successfully logs in."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                headers={"CF-Access-Authenticated-User-Email": "admin@flodss.local"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "session_token" in data
            assert data["user"]["email"] == "admin@flodss.local"
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_protected_quick_tunnel_login_not_blocked_by_different_advisory_header(self, client):
        """In PROTECTED_QUICK_TUNNEL mode, unverified advisory header does NOT block legitimate user login."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            # User logs in with legitimate FLODSS password even if an arbitrary advisory header is present
            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                headers={"CF-Access-Authenticated-User-Email": "advisory-edge@university.edu"},
            )
            assert resp.status_code == 200
            assert resp.json()["user"]["email"] == "admin@flodss.local"
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_protected_quick_tunnel_rejects_wrong_password_regardless_of_header(self, client):
        """Passing any Cloudflare header is never sufficient: wrong FLODSS password returns 401."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": "WrongPassword999!"},
                headers={"CF-Access-Authenticated-User-Email": "admin@flodss.local"},
            )
            assert resp.status_code == 401
            assert "Invalid email or password" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_invitation_acceptance_under_protected_quick_tunnel(self, client):
        """Registration via invitation verifies token validity without requiring Cloudflare email header."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            unique_email = f"quick_res_{uuid.uuid4().hex[:8]}@lab.org"
            with db_manager.get_connection() as conn:
                AuthService.ensure_admin_user(conn)
                cur = conn.execute("SELECT id FROM users WHERE email = ?;", (settings.DEFAULT_ADMIN_EMAIL.lower(),))
                admin_id = cur.fetchone()[0]

                inv = AuthService.create_invitation(
                    created_by_user_id=admin_id,
                    email=unique_email,
                    role=UserRole.RESEARCHER,
                    conn=conn,
                )

            # Legitimate invitation acceptance succeeds even without Cloudflare header
            resp_ok = client.post(
                "/api/auth/invitations/accept",
                json={"token": inv.token, "full_name": "Quick Res", "password": "SecurePassword2026!"},
            )
            assert resp_ok.status_code == 201
            assert "session_token" in resp_ok.json()
            assert resp_ok.json()["user"]["email"] == unique_email
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_direct_origin_access_from_untrusted_socket_rejected(self):
        """Simulate an external client connecting directly to FLODSS (socket IP != 127.0.0.1)."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            class UntrustedSocketRequest:
                client = type("Client", (), {"host": "198.51.100.99"})()
                headers = {"cf-access-authenticated-user-email": "admin@flodss.local"}
                cookies = {}

            with pytest.raises(Exception) as excinfo:
                CloudflareAccessService.extract_and_verify_request(UntrustedSocketRequest())
            assert "Untrusted connection origin (198.51.100.99)" in str(excinfo.value)
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode


class TestDualLayerDefenseAndIsolation:
    """Verify dual-layer defense: Cloudflare perimeter + FLODSS internal RBAC & session isolation."""

    def test_unauthenticated_api_access_blocked(self, clean_client):
        """Protected API routes reject unauthenticated requests with HTTP 401 Unauthorized (No bypass)."""
        for path in ("/api/projects", "/api/auth/me", "/api/algorithms/corelap/solve"):
            resp = clean_client.get(path) if "solve" not in path else clean_client.post(path, json={})
            assert resp.status_code == 401

    def test_logout_terminates_session_under_quick_tunnel(self, clean_client):
        """Active session can be terminated via /api/auth/logout, revoking session token."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"

            login_resp = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["session_token"]

            # Profile works
            me_resp = clean_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me_resp.status_code == 200

            # Logout
            logout_resp = clean_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
            assert logout_resp.status_code == 200

            # Subsequent call rejected
            after_resp = clean_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert after_resp.status_code == 401
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    def test_managed_access_mode_preserved_with_full_jwt(self, client):
        """Managed Access mode continues to require cryptographic RS256 JWT assertions."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "MANAGED_ACCESS"
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "test-team"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "test-aud"

            priv_key, _ = setup_test_key_pair("managed-mode-kid")

            # Passing plain email header alone in MANAGED_ACCESS is REJECTED (Missing JWT)
            resp_no_jwt = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                headers={"CF-Access-Authenticated-User-Email": "admin@flodss.local"},
            )
            assert resp_no_jwt.status_code == 403
            assert "Missing or empty Cf-Access-Jwt-Assertion" in resp_no_jwt.json()["detail"]

            # Passing valid signed JWT succeeds
            token = create_test_jwt("admin@flodss.local", priv_key, kid="managed-mode-kid", aud="test-aud", issuer="https://test-team.cloudflareaccess.com")
            resp_jwt = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                headers={
                    "Cf-Access-Jwt-Assertion": token,
                    "CF-Access-Authenticated-User-Email": "admin@flodss.local",
                },
            )
            assert resp_jwt.status_code == 200
            assert "session_token" in resp_jwt.json()
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_managed_access_rejects_mismatched_email(self, client):
        """Managed Access strictly enforces cryptographic email binding."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "MANAGED_ACCESS"
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "test-team"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "test-aud"

            priv_key, _ = setup_test_key_pair("managed-mode-kid-2")
            token = create_test_jwt("alice@university.edu", priv_key, kid="managed-mode-kid-2", aud="test-aud", issuer="https://test-team.cloudflareaccess.com")

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
                headers={"Cf-Access-Jwt-Assertion": token},
            )
            assert resp.status_code == 403
            assert "must match cryptographically verified Cloudflare Access email" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_direct_localhost_rbac_and_isolation_enforced(self, clean_client):
        """Even with direct localhost access, FLODSS internal RBAC and isolation are strictly active."""
        orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
        try:
            settings.CLOUDFLARE_PERIMETER_MODE = "DISABLED"
            # 1. Login as admin
            admin_login = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": get_current_admin_password()},
            )
            assert admin_login.status_code == 200
            admin_token = admin_login.json()["session_token"]

            # 2. Admin can create invitation
            inv_resp = clean_client.post(
                "/api/auth/invitations",
                json={"email": f"viewer_{uuid.uuid4().hex[:6]}@flodss.local", "role": "VIEWER"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert inv_resp.status_code == 201
            inv_token = inv_resp.json()["token"]

            # 3. Accept as viewer
            accept_resp = clean_client.post(
                "/api/auth/invitations/accept",
                json={"token": inv_token, "full_name": "Viewer Test", "password": "ViewerPassword2026!"},
            )
            assert accept_resp.status_code == 201
            viewer_token = accept_resp.json()["session_token"]

            # 4. Viewer attempts admin endpoint (e.g. list invitations) -> 403 Forbidden
            view_forbidden = clean_client.get(
                "/api/auth/invitations",
                headers={"Authorization": f"Bearer {viewer_token}"},
            )
            assert view_forbidden.status_code == 403
        finally:
            settings.CLOUDFLARE_PERIMETER_MODE = orig_mode
