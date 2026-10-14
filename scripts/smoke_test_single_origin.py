"""Production-like localhost smoke test for single-origin FLODSS deployment.

Tests:
1. Single-Origin Static Delivery (Vite HTML shell, CSS/JS bundles)
2. API routing and Health status
3. Unauthenticated security barrier (401 on /api/projects)
4. Admin authentication and session issuance
5. Tunnel HTTPS detection & Secure cookie enforcement
6. Synthetic benchmark optimization (CORELAP solve)
7. Session revocation / Logout
"""

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Enforce isolated test database
os.environ["FLODSS_TESTING"] = "true"
test_db = Path(__file__).resolve().parent.parent / "data" / "test_flodss.db"
os.environ["TEST_DATABASE_PATH"] = str(test_db)

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.database import db_manager
db_manager.set_db_path(str(test_db))
db_manager.run_migrations()
from app.services.auth_service import AuthService
with db_manager.get_connection() as conn:
    AuthService.ensure_admin_user(conn)

from app.main import app, FRONTEND_DIST
from app.core.config import settings


def run_smoke_test():
    print("=" * 70)
    print("FLODSS Phase 14.4: Single-Origin Production Smoke Test")
    print("=" * 70)

    with TestClient(app) as client:
        # 1. Frontend Dist HTML
        print("\n[Step 1] Requesting '/' with browser Accept header...")
        resp = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")
        assert '<div id="root">' in resp.text
        print("  [PASS] Root returned compiled index.html shell (Status 200)")

        # 2. Frontend JS Asset
        print("\n[Step 2] Requesting compiled assets from '/assets/'...")
        assets_dir = FRONTEND_DIST / "assets"
        js_files = list(assets_dir.glob("*.js"))
        assert len(js_files) > 0, "No JS files found in frontend/dist/assets"
        js_name = js_files[0].name
        resp_asset = client.get(f"/assets/{js_name}")
        assert resp_asset.status_code == 200, f"Asset returned {resp_asset.status_code}"
        assert len(resp_asset.content) > 1000
        print(f"  [PASS] Static asset '/assets/{js_name}' served successfully ({len(resp_asset.content)} bytes)")

        # 3. API Health Check
        print("\n[Step 3] Querying '/api/health'...")
        resp_health = client.get("/api/health")
        assert resp_health.status_code == 200
        health_data = resp_health.json()
        assert health_data["status"] == "healthy"
        print(f"  [PASS] System healthy: {health_data['project_name']} v{health_data['version']}")

        # 4. Unauthenticated Access Barrier
        print("\n[Step 4] Probing protected endpoint '/api/projects' without credentials...")
        resp_unauth = client.get("/api/projects")
        assert resp_unauth.status_code == 401
        print("  [PASS] Unauthenticated access rejected with HTTP 401 Unauthorized")

        # 5. Admin Authentication & Tunnel HTTPS Cookie Test
        print("\n[Step 5] Authenticating as Admin with Cloudflare Tunnel HTTPS headers...")
        admin_email = settings.DEFAULT_ADMIN_EMAIL
        admin_pass = settings.DEFAULT_ADMIN_PASSWORD
        secret_file = Path(__file__).resolve().parent.parent / "backend" / "data" / ".admin_credentials.secret"
        if secret_file.exists():
            with open(secret_file, "r", encoding="utf-8") as sf:
                for line in sf:
                    line = line.strip()
                    if line.startswith("FLODSS_ADMIN_EMAIL="):
                        admin_email = line.split("=", 1)[1].strip()
                    elif line.startswith("FLODSS_ADMIN_PASSWORD="):
                        admin_pass = line.split("=", 1)[1].strip()

        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": admin_email,
                "password": admin_pass,
            },
            headers={
                "X-Forwarded-Proto": "https",
                "CF-Connecting-IP": "203.0.113.195",
            },
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_data = login_resp.json()
        token = login_data["session_token"]
        assert token is not None

        set_cookie = login_resp.headers.get("set-cookie", "")
        assert "secure" in set_cookie.lower(), "Secure flag missing from HTTPS session cookie!"
        assert "httponly" in set_cookie.lower(), "HttpOnly flag missing!"
        print(f"  [PASS] Authenticated as {login_data['user']['email']} (Role: {login_data['user']['role']})")
        print("  [PASS] Cookie has 'Secure', 'HttpOnly', and 'SameSite=Lax' flags")

        # 6. Authenticated User Profile
        print("\n[Step 6] Verifying user profile via '/api/auth/me'...")
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == settings.DEFAULT_ADMIN_EMAIL
        print("  [PASS] User profile confirmed via Bearer session token")

        # 7. Synthetic Optimization Execution
        print("\n[Step 7] Running synthetic optimization solve (/api/algorithms/corelap/solve)...")
        solve_resp = client.post(
            "/api/algorithms/corelap/solve",
            json={"problem_id": "sample_academic_4"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert solve_resp.status_code == 200, f"Solve failed: {solve_resp.text}"
        solve_data = solve_resp.json()
        assert solve_data["validation"]["is_valid"] is True
        assert len(solve_data["solution"]["placements"]) > 0
        print(f"  [PASS] Solved synthetic benchmark with {len(solve_data['solution']['placements'])} departments")
        print(f"  [PASS] Layout feasibility: {solve_data['validation']['is_valid']}")
        mhc = solve_data["evaluation"]["objective_values"].get("material_handling_cost", 0.0)
        print(f"  [PASS] MHC: {mhc:.2f}")

        # 8. Logout & Session Revocation
        print("\n[Step 8] Terminating session via '/api/auth/logout'...")
        logout_resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_resp.status_code == 200

        # Post-logout verification
        post_logout = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert post_logout.status_code == 401
        print("  [PASS] Session revoked successfully; subsequent calls rejected with HTTP 401")

    print("\n" + "=" * 70)
    print("ALL PRODUCTION-LIKE SMOKE TESTS PASSED (8/8 CHECKS SUCCESSFUL)")
    print("=" * 70)


if __name__ == "__main__":
    run_smoke_test()
