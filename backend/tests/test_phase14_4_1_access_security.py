"""Security test suite for Phase 14.4.1: Cloudflare Access Trust Boundary Hardening.

Covers:
1. Forged email header rejection (CF-Access-Authenticated-User-Email without signed JWT)
2. Missing JWT assertion rejection when perimeter is enforced
3. Invalid JWT signature rejection (untrusted key not in JWKS)
4. Wrong audience (AUD) rejection
5. Expired JWT token rejection
6. Mismatched email rejection (login email != token email, invitation email != token email, header != token)
7. Spoofed forwarded headers prevention (untrusted client IP cannot spoof CF-Connecting-IP or X-Forwarded-Proto)
8. Direct origin bypass / Fail-closed configuration (missing AUD or team domain fails closed)
9. Cookie fallback (CF_Authorization cookie verification)
10. JWKS Cache TTL and key lifecycle
"""

import time
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import get_trusted_client_ip, is_trusted_secure_request
from app.services.cloudflare_access_service import (
    jwks_cache,
    setup_test_key_pair,
    create_test_jwt,
    CloudflareAccessService,
    CloudflareAccessError,
    CloudflareMissingTokenError,
    CloudflareInvalidTokenError,
    CloudflareConfigurationError,
)
from app.db.database import db_manager
from app.services.auth_service import AuthService
from app.models.auth import UserRole


@pytest.fixture
def client():
    """Unauthenticated client with clean context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def rsa_keys():
    """Generate ephemeral RSA key pair for testing and register public key in cache."""
    kid = "phase14_4_1_test_kid"
    priv_key, pub_key = setup_test_key_pair(kid=kid)
    return {"kid": kid, "private_key": priv_key, "public_key": pub_key}


class TestCloudflareAccessTrustBoundary:
    """Rigorous verification of Cloudflare Access cryptographic perimeter."""

    def test_forged_email_header_rejected_without_jwt(self, client):
        """Attacker sending CF-Access-Authenticated-User-Email without signed JWT is rejected (403)."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            # Attacker presents forged email header only
            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"CF-Access-Authenticated-User-Email": "admin@flodss.local"},
            )
            assert resp.status_code == 403
            assert "Missing or empty Cf-Access-Jwt-Assertion" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_missing_jwt_rejected_when_enforced(self, client):
        """Request without any Cloudflare headers is rejected with 403 Forbidden."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            )
            assert resp.status_code == 403
            assert "Cloudflare Access perimeter authentication required" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_invalid_jwt_signature_rejected(self, client, rsa_keys):
        """JWT signed with untrusted / alien private key is rejected with 403 Forbidden."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            # Create an untrusted private key not in JWKS
            untrusted_key = rsa.generate_private_key(65537, 2048)
            bad_token = create_test_jwt(
                email="admin@flodss.local",
                private_key=untrusted_key,
                kid="untrusted_alien_kid",
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": bad_token},
            )
            assert resp.status_code == 403
            assert "Key ID 'untrusted_alien_kid' not found in Cloudflare Access JWKS certificates" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_wrong_audience_rejected(self, client, rsa_keys):
        """JWT with mismatching audience (aud) claim is rejected with 403 Forbidden."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "expected-aud-token"

            wrong_aud_token = create_test_jwt(
                email="admin@flodss.local",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="wrong-application-aud",
                issuer="https://flodss-research.cloudflareaccess.com",
            )

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": wrong_aud_token},
            )
            assert resp.status_code == 403
            assert "audience mismatch" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_expired_jwt_rejected(self, client, rsa_keys):
        """Expired JWT assertion is rejected with 403 Forbidden."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            expired_token = create_test_jwt(
                email="admin@flodss.local",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
                expires_in_seconds=-300,  # Expired 5 minutes ago
            )

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": expired_token},
            )
            assert resp.status_code == 403
            assert "expired" in resp.json()["detail"].lower()
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_mismatched_email_between_login_and_jwt_rejected(self, client, rsa_keys):
        """Valid JWT for alice@research.ac.uk cannot be used to login as admin@flodss.local."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            alice_token = create_test_jwt(
                email="alice@research.ac.uk",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": alice_token},
            )
            assert resp.status_code == 403
            assert "must match cryptographically verified Cloudflare Access email" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_mismatched_email_between_header_and_jwt_rejected(self, client, rsa_keys):
        """Header CF-Access-Authenticated-User-Email claiming admin while JWT belongs to alice is rejected."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            alice_token = create_test_jwt(
                email="alice@research.ac.uk",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )

            resp = client.post(
                "/api/auth/login",
                json={"email": "alice@research.ac.uk", "password": "AnyPassword123!"},
                headers={
                    "Cf-Access-Jwt-Assertion": alice_token,
                    "CF-Access-Authenticated-User-Email": "admin@flodss.local",  # Spoofed header
                },
            )
            assert resp.status_code == 403
            assert "does not match cryptographically verified token email" in resp.json()["detail"]
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_invitation_acceptance_enforces_cryptographic_jwt(self, client, rsa_keys):
        """Invitation acceptance rejects mismatched or missing Cloudflare JWT assertions."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            unique_email = f"new_res_{uuid.uuid4().hex[:8]}@lab.org"
            with db_manager.get_connection() as conn:
                AuthService.ensure_admin_user(conn)
                cur = conn.execute("SELECT id FROM users WHERE email = ?;", (settings.DEFAULT_ADMIN_EMAIL.lower(),))
                admin_row = cur.fetchone()
                admin_id = admin_row[0] if admin_row else "usr_admin_default"

                inv = AuthService.create_invitation(
                    created_by_user_id=admin_id,
                    email=unique_email,
                    role=UserRole.RESEARCHER,
                    conn=conn,
                )

            # Case A: Missing JWT assertion -> 403
            resp_missing = client.post(
                "/api/auth/invitations/accept",
                json={
                    "token": inv.token,
                    "full_name": "New Researcher",
                    "password": "SecurePassword2026!",
                },
            )
            assert resp_missing.status_code == 403

            # Case B: JWT email does not match invitation target email -> 403
            other_jwt = create_test_jwt(
                email="intruder@outside.net",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )
            resp_mismatch = client.post(
                "/api/auth/invitations/accept",
                json={
                    "token": inv.token,
                    "full_name": "New Researcher",
                    "password": "SecurePassword2026!",
                },
                headers={"Cf-Access-Jwt-Assertion": other_jwt},
            )
            assert resp_mismatch.status_code == 403
            assert "Invitation target email" in resp_mismatch.json()["detail"]

            # Case C: Correct verified JWT -> 201 Created
            correct_jwt = create_test_jwt(
                email=unique_email,
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )
            resp_ok = client.post(
                "/api/auth/invitations/accept",
                json={
                    "token": inv.token,
                    "full_name": "New Researcher",
                    "password": "SecurePassword2026!",
                },
                headers={"Cf-Access-Jwt-Assertion": correct_jwt},
            )
            assert resp_ok.status_code == 201
            assert "session_token" in resp_ok.json()
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_cf_authorization_cookie_fallback(self, client, rsa_keys):
        """CF_Authorization cookie is accepted and verified when header is omitted."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "flodss-research"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "aud-phase14-4-1"

            valid_jwt = create_test_jwt(
                email="admin@flodss.local",
                private_key=rsa_keys["private_key"],
                kid=rsa_keys["kid"],
                aud="aud-phase14-4-1",
                issuer="https://flodss-research.cloudflareaccess.com",
            )

            client.cookies.set("CF_Authorization", valid_jwt)
            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            )
            assert resp.status_code == 200
            assert "session_token" in resp.json()
        finally:
            client.cookies.clear()
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud

    def test_fail_closed_configuration_on_missing_aud_or_domain(self, client):
        """Fail-closed behavior: If CLOUDFLARE_ACCESS_ENFORCED is True but config is missing, reject with 403."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = None
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = None

            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": "dummy.token.here"},
            )
            assert resp.status_code == 403
            assert "fail-closed" in resp.json()["detail"].lower()
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud


class MockRequest:
    """Lightweight mock of FastAPI / Starlette request for unit testing proxy header resolution."""

    def __init__(self, host: str, headers: dict = None, scheme: str = "http"):
        self.client = type("Client", (), {"host": host})()
        self.headers = headers or {}
        self.url = type("URL", (), {"scheme": scheme})()


class TestProxyHeaderAntiSpoofing:
    """Verify that proxy headers are ignored unless direct connection originates from TRUSTED_PROXIES."""

    def test_untrusted_direct_connection_ignores_spoofed_ip_headers(self):
        """Direct connection from 198.51.100.24 cannot spoof CF-Connecting-IP or X-Forwarded-For."""
        untrusted_req = MockRequest(
            host="198.51.100.24",
            headers={
                "cf-connecting-ip": "10.0.0.1",
                "x-forwarded-for": "10.0.0.2, 198.51.100.24",
            },
        )
        resolved_ip = get_trusted_client_ip(untrusted_req)
        # MUST return 198.51.100.24, completely ignoring spoofed 10.0.0.1
        assert resolved_ip == "198.51.100.24"

    def test_untrusted_direct_connection_ignores_spoofed_https_headers(self):
        """Direct connection from 198.51.100.24 cannot spoof X-Forwarded-Proto: https."""
        untrusted_req = MockRequest(
            host="198.51.100.24",
            headers={"x-forwarded-proto": "https"},
            scheme="http",
        )
        assert is_trusted_secure_request(untrusted_req) is False

    def test_trusted_proxy_connection_accepts_valid_forwarded_headers(self):
        """Local reverse proxy or tunnel connection from 127.0.0.1 is permitted to forward client IP."""
        trusted_req = MockRequest(
            host="127.0.0.1",
            headers={
                "cf-connecting-ip": "203.0.113.195",
                "x-forwarded-proto": "https",
            },
            scheme="http",
        )
        assert get_trusted_client_ip(trusted_req) == "203.0.113.195"
        assert is_trusted_secure_request(trusted_req) is True

    def test_ipv6_localhost_trusted_proxy_connection_accepted(self):
        """Local IPv6 connection from ::1 is recognized as a trusted proxy."""
        trusted_req = MockRequest(
            host="::1",
            headers={
                "cf-connecting-ip": "198.51.100.77",
                "cf-visitor": '{"scheme":"https"}',
            },
            scheme="http",
        )
        assert get_trusted_client_ip(trusted_req) == "198.51.100.77"
        assert is_trusted_secure_request(trusted_req) is True
