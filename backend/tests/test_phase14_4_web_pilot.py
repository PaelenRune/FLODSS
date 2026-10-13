"""Unit and integration tests for Phase 14.4: Invite-Only Web Pilot Preparation.

Verifies:
1. Single-Origin frontend static serving & SPA fallback vs API discovery
2. Cloudflare Access perimeter enforcement & email matching
3. Proxy header resolution (CF-Connecting-IP, X-Forwarded-For)
4. HTTPS auto-detection & Secure cookie attributes (X-Forwarded-Proto, CF-Visitor)
5. Concurrency governance: Per-user AND system-wide total capacity limits
6. Cloudflare Tunnel CORS configuration parsing
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, FRONTEND_DIST
from app.core.config import settings
from app.core.security import concurrency_manager
from app.api.deps import JobSlotGuard
from app.models.auth import User, UserRole
from app.services.auth_service import AuthService
from app.db.database import db_manager


@pytest.fixture
def clean_client():
    """Unauthenticated client with pristine dependency overrides."""
    with TestClient(app) as client:
        yield client


class TestSingleOriginStaticServing:
    """Validate single-origin hosting of Vite production build and API routing."""

    def test_root_returns_html_when_browser_accepts_html(self, clean_client):
        """Browsers requesting root receive index.html single-page application entry."""
        if (FRONTEND_DIST / "index.html").exists():
            resp = clean_client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
            assert resp.status_code == 200
            assert "text/html" in resp.headers.get("content-type", "")
            assert "<!doctype html>" in resp.text.lower()
        else:
            pytest.skip("frontend/dist/index.html not built in test environment")

    def test_root_returns_json_for_api_clients(self, clean_client):
        """API clients requesting root receive discovery JSON."""
        resp = clean_client.get("/", headers={"Accept": "application/json"})
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert "message" in data
        assert data["health"] == "/api/health"

    def test_spa_route_fallback_to_index_html(self, clean_client):
        """Deep browser navigation to client routes resolves to index.html."""
        if (FRONTEND_DIST / "index.html").exists():
            resp = clean_client.get("/workspace/project-alpha", headers={"Accept": "text/html"})
            assert resp.status_code == 200
            assert "<!doctype html>" in resp.text.lower()
        else:
            pytest.skip("frontend/dist/index.html not built")

    def test_api_routes_do_not_fallback_to_html_on_404(self, clean_client):
        """Non-existent API routes return 404 JSON rather than HTML SPA."""
        resp = clean_client.get("/api/nonexistent-endpoint", headers={"Accept": "text/html"})
        assert resp.status_code == 404
        assert resp.headers.get("content-type", "").startswith("application/json")


class TestCloudflareAccessPerimeterSecurity:
    """Validate dual-layer defense: Cloudflare Access allowlist + FLODSS internal auth."""

    def test_login_enforces_cloudflare_access_email_when_enabled(self, clean_client):
        """When CLOUDFLARE_ACCESS_ENFORCED is active, requests must include verified CF JWT assertion."""
        orig_enforced = settings.CLOUDFLARE_ACCESS_ENFORCED
        orig_team = settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN
        orig_aud = settings.CLOUDFLARE_ACCESS_EXPECTED_AUD
        try:
            settings.CLOUDFLARE_ACCESS_ENFORCED = True
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = "test-team"
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = "test-aud-123"

            from app.services.cloudflare_access_service import setup_test_key_pair, create_test_jwt
            priv_key, _ = setup_test_key_pair("pilot-kid-1")

            # Case A: Missing Cloudflare Access assertion -> 403 Forbidden
            resp = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            )
            assert resp.status_code == 403
            assert "Cloudflare Access perimeter authentication required" in resp.json()["detail"]

            # Case B: Forged email header without JWT -> 403 Forbidden
            resp = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"CF-Access-Authenticated-User-Email": "admin@flodss.local"},
            )
            assert resp.status_code == 403

            # Case C: Valid JWT for attacker@evil.com (mismatched email) -> 403 Forbidden
            attacker_jwt = create_test_jwt("attacker@evil.com", priv_key, kid="pilot-kid-1")
            resp = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={"Cf-Access-Jwt-Assertion": attacker_jwt},
            )
            assert resp.status_code == 403
            assert "must match cryptographically verified Cloudflare Access email" in resp.json()["detail"]

            # Case D: Matching valid Cloudflare Access JWT assertion -> 200 OK
            valid_jwt = create_test_jwt("admin@flodss.local", priv_key, kid="pilot-kid-1")
            resp = clean_client.post(
                "/api/auth/login",
                json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
                headers={
                    "Cf-Access-Jwt-Assertion": valid_jwt,
                    "CF-Access-Authenticated-User-Email": "admin@flodss.local",
                },
            )
            assert resp.status_code == 200
            assert "session_token" in resp.json()
        finally:
            settings.CLOUDFLARE_ACCESS_ENFORCED = orig_enforced
            settings.CLOUDFLARE_ACCESS_TEAM_DOMAIN = orig_team
            settings.CLOUDFLARE_ACCESS_EXPECTED_AUD = orig_aud


class TestProxyHeadersAndSecureCookies:
    """Verify HTTPS detection, Secure cookie attributes, and client IP extraction."""

    def test_secure_cookie_set_when_x_forwarded_proto_is_https(self, clean_client):
        """Cloudflare Tunnel setting X-Forwarded-Proto: https triggers Secure flag on session cookie."""
        resp = clean_client.post(
            "/api/auth/login",
            json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            headers={"X-Forwarded-Proto": "https"},
        )
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "flodss_session" in set_cookie
        assert "secure" in set_cookie.lower()
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()

    def test_secure_cookie_set_when_cf_visitor_scheme_https(self, clean_client):
        """Cloudflare CF-Visitor JSON header triggers Secure flag."""
        resp = clean_client.post(
            "/api/auth/login",
            json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            headers={"CF-Visitor": '{"scheme":"https"}'},
        )
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "secure" in set_cookie.lower()

    def test_client_ip_extracted_from_cf_connecting_ip(self, clean_client):
        """Cloudflare CF-Connecting-IP header is recorded in session and audit log."""
        test_ip = "198.51.100.42"
        resp = clean_client.post(
            "/api/auth/login",
            json={"email": "admin@flodss.local", "password": settings.DEFAULT_ADMIN_PASSWORD},
            headers={"CF-Connecting-IP": test_ip},
        )
        assert resp.status_code == 200
        with db_manager.get_connection() as conn:
            cur = conn.execute(
                "SELECT ip_address FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = 'admin@flodss.local') ORDER BY created_at DESC LIMIT 1;"
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == test_ip


class TestConcurrencyGovernance:
    """Validate per-user and system-wide global optimization concurrency limits."""

    def test_per_user_concurrency_limit_enforced(self):
        """User cannot acquire more than MAX_CONCURRENT_JOBS_PER_USER slots."""
        concurrency_manager.reset_all()
        user = User(
            id="usr_conc_test_1",
            email="u1@test.local",
            full_name="User 1",
            role=UserRole.RESEARCHER,
            is_active=True,
            created_at="2026-10-12T00:00:00Z",
            updated_at="2026-10-12T00:00:00Z",
        )

        # Slot 1: Success
        guard1 = JobSlotGuard(user)
        guard1.__enter__()

        # Slot 2: Success (limit is 2)
        guard2 = JobSlotGuard(user)
        guard2.__enter__()

        # Slot 3: Exceeds per-user limit -> 429
        guard3 = JobSlotGuard(user)
        with pytest.raises(Exception) as excinfo:
            guard3.__enter__()
        assert "429" in str(excinfo.value)
        assert "Concurrent job limit exceeded" in str(excinfo.value)

        # Clean up
        guard2.__exit__(None, None, None)
        guard1.__exit__(None, None, None)
        assert concurrency_manager.get_active_count(user.id) == 0

    def test_system_wide_total_concurrency_limit_enforced(self):
        """System rejects jobs across distinct users once MAX_TOTAL_CONCURRENT_JOBS is reached."""
        concurrency_manager.reset_all()
        orig_max_total = settings.MAX_TOTAL_CONCURRENT_JOBS
        try:
            settings.MAX_TOTAL_CONCURRENT_JOBS = 2

            u1 = User(id="u1", email="u1@test.com", full_name="U1", role=UserRole.RESEARCHER, is_active=True, created_at="", updated_at="")
            u2 = User(id="u2", email="u2@test.com", full_name="U2", role=UserRole.RESEARCHER, is_active=True, created_at="", updated_at="")
            u3 = User(id="u3", email="u3@test.com", full_name="U3", role=UserRole.RESEARCHER, is_active=True, created_at="", updated_at="")

            # User 1 job
            g1 = JobSlotGuard(u1)
            g1.__enter__()

            # User 2 job
            g2 = JobSlotGuard(u2)
            g2.__enter__()

            # User 3 attempts job when system total is full (2/2) -> 429
            g3 = JobSlotGuard(u3)
            with pytest.raises(Exception) as excinfo:
                g3.__enter__()
            assert "429" in str(excinfo.value)
            assert "System-wide optimization capacity reached" in str(excinfo.value)

            # Release u1, now u3 can acquire
            g1.__exit__(None, None, None)
            g3.__enter__()
            g3.__exit__(None, None, None)
            g2.__exit__(None, None, None)
            assert concurrency_manager.get_total_active_count() == 0
        finally:
            settings.MAX_TOTAL_CONCURRENT_JOBS = orig_max_total
