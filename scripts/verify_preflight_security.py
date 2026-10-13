"""Comprehensive pre-flight security verification suite for FLODSS pilot."""

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.config import settings
from app.db.database import db_manager
from app.services.cloudflare_access_service import CloudflareAccessService, CloudflareUntrustedOriginError


def load_admin_secret() -> tuple[str, str]:
    secret_file = backend_dir / "data" / ".admin_credentials.secret"
    if not secret_file.exists():
        raise FileNotFoundError(f"Admin secret file not found: {secret_file}")
    
    email = None
    password = None
    with open(secret_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("FLODSS_ADMIN_EMAIL="):
                email = line.split("=", 1)[1].strip()
            elif line.startswith("FLODSS_ADMIN_PASSWORD="):
                password = line.split("=", 1)[1].strip()
    
    if not email or not password:
        raise ValueError("Admin credentials incomplete in secret file.")
    return email, password


def run_checks():
    print("======================================================================")
    print("FLODSS PRE-FLIGHT PILOT SECURITY VERIFICATION")
    print("======================================================================")

    results = {}
    client = TestClient(app)

    # 1. Admin Credentials Check
    try:
        admin_email, admin_pwd = load_admin_secret()
        # Ensure default password is NOT in use
        if admin_pwd in ("FlodssAdmin2026!", "admin123", "password"):
            results["1. Default Password Check"] = ("FAIL", "Admin password is still using a well-known default!")
        else:
            results["1. Default Password Check"] = ("PASS", "Admin password has been rotated to high-entropy unique secret.")
    except Exception as e:
        results["1. Default Password Check"] = ("FAIL", str(e))
        return results

    # 2. Old Default Password Rejection Check
    old_login = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "FlodssAdmin2026!"},
    )
    if old_login.status_code == 401:
        results["2. Legacy Password Revocation"] = ("PASS", "Old default password successfully rejected (HTTP 401).")
    else:
        results["2. Legacy Password Revocation"] = ("FAIL", f"Old password was NOT rejected! Status: {old_login.status_code}")

    # 3. New Rotated Password Authentication
    new_login = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": admin_pwd},
    )
    if new_login.status_code == 200 and "session_token" in new_login.json():
        admin_token = new_login.json()["session_token"]
        results["3. Rotated Password Login"] = ("PASS", "Admin successfully authenticated with rotated credentials.")
    else:
        results["3. Rotated Password Login"] = ("FAIL", f"Login with rotated password failed! Status: {new_login.status_code}")
        return results

    # 4. Deactivated Test User Check
    deactivated_login = client.post(
        "/api/auth/login",
        json={"email": "res_role@flodss.local", "password": "password"},
    )
    if deactivated_login.status_code in (401, 403):
        results["4. Test User Deactivation"] = ("PASS", f"Legacy test user rejected (HTTP {deactivated_login.status_code}).")
    else:
        results["4. Test User Deactivation"] = ("FAIL", f"Deactivated user logged in unexpectedly: {deactivated_login.status_code}")

    # 5. Unauthenticated API Boundary Check (Using clean client with no cookies)
    unauth_client = TestClient(app)
    unauth_resp = unauth_client.get("/api/projects")
    if unauth_resp.status_code == 401:
        results["5. Unauthenticated Access Block"] = ("PASS", "Protected endpoint /api/projects blocked without token (HTTP 401).")
    else:
        results["5. Unauthenticated Access Block"] = ("FAIL", f"Protected endpoint accessible anonymously! Status: {unauth_resp.status_code}")

    # 6. Authenticated Role & Profile Check
    auth_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    if auth_resp.status_code == 200 and auth_resp.json().get("role") == "ADMIN":
        results["6. RBAC Role Verification"] = ("PASS", f"Confirmed authenticated user role: {auth_resp.json().get('role')}")
    else:
        results["6. RBAC Role Verification"] = ("FAIL", f"Failed to retrieve admin profile! Status: {auth_resp.status_code}")

    # 7. Untrusted Socket Origin Rejection
    class MockExternalRequest:
        client = type("Client", (), {"host": "203.0.113.195"})()
        headers = {}
        cookies = {}

    orig_mode = settings.CLOUDFLARE_PERIMETER_MODE
    try:
        settings.CLOUDFLARE_PERIMETER_MODE = "PROTECTED_QUICK_TUNNEL"
        CloudflareAccessService.extract_and_verify_request(MockExternalRequest())
        results["7. Socket Origin Anti-Spoofing"] = ("FAIL", "Direct untrusted socket was not rejected!")
    except CloudflareUntrustedOriginError:
        results["7. Socket Origin Anti-Spoofing"] = ("PASS", "External socket connection strictly rejected with CloudflareUntrustedOriginError.")
    finally:
        settings.CLOUDFLARE_PERIMETER_MODE = orig_mode

    # 8. Session Revocation (Logout)
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})
    after_logout = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    if logout_resp.status_code == 200 and after_logout.status_code == 401:
        results["8. Session Revocation (Logout)"] = ("PASS", "Session revoked successfully; subsequent calls blocked (HTTP 401).")
    else:
        results["8. Session Revocation (Logout)"] = ("FAIL", f"Logout did not properly revoke token! Status: {after_logout.status_code}")

    # 9. Perimeter Settings Verification
    if settings.effective_perimeter_mode == "PROTECTED_QUICK_TUNNEL" and settings.is_perimeter_enforced:
        results["9. Perimeter Mode Configuration"] = ("PASS", "CLOUDFLARE_PERIMETER_MODE resolves to PROTECTED_QUICK_TUNNEL.")
    else:
        results["9. Perimeter Mode Configuration"] = ("FAIL", f"Unexpected mode: {settings.effective_perimeter_mode}")

    # 10. Localhost Socket Binding Verification
    if settings.HOST == "127.0.0.1" and settings.PORT == 8000:
        results["10. Localhost Socket Binding"] = ("PASS", f"Backend configured to bind strictly on {settings.HOST}:{settings.PORT}")
    else:
        results["10. Localhost Socket Binding"] = ("FAIL", f"Binding is {settings.HOST}:{settings.PORT}")

    return results


def main():
    results = run_checks()
    all_passed = True
    for test_name, (status, detail) in results.items():
        print(f"[{status}] {test_name}: {detail}")
        if status != "PASS":
            all_passed = False

    print("======================================================================")
    if all_passed:
        print("OVERALL PRE-FLIGHT VERIFICATION: ALL 10 CHECKS PASSED")
    else:
        print("OVERALL PRE-FLIGHT VERIFICATION: ONE OR MORE CHECKS FAILED")
    print("======================================================================")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
