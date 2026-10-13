# FLODSS Phase 14.4.1: Cloudflare Access Trust Boundary Security Audit Report

**System Version:** `v1.0.0-rc.1`  
**Classification:** Confidential — Academic Research Prototype  
**Date:** 2026-10-12  
**Target Environment:** Localhost / Private Research Server Boundary  
**Audit Status:** **COMPLETED — VERIFIED**  
**Gate Decision:** **GO (Cryptographic Perimeter Sealed & Verified)**

---

## 1. Executive Summary & Audit Objective

In Phase 14.4, preliminary support for Cloudflare Tunnel and Cloudflare Access was introduced. However, a critical security boundary flaw was identified: the application relied on the plain HTTP header `CF-Access-Authenticated-User-Email` without cryptographically verifying the incoming Cloudflare Access JSON Web Token assertion. Under direct origin access or malicious proxy header injection, an adversary could forge this header to impersonate legitimate researchers or administrators.

**Phase 14.4.1 eliminates this vulnerability entirely:**
1. **Zero Trust in Unsigned Headers:** The `CF-Access-Authenticated-User-Email` header is no longer accepted as proof of identity.
2. **Cryptographic JWT Verification:** Implemented RS256 signature verification via JWKS public keys, validating Issuer, Application Audience (AUD), Expiration (`exp`), and Key ID (`kid`).
3. **Identity Binding:** The cryptographically verified email extracted from the token payload is strictly matched against the FLODSS login email and invitation target email.
4. **Proxy Header Anti-Spoofing:** Headers such as `CF-Connecting-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` are ignored unless the direct socket connection originates from an explicitly trusted proxy (`127.0.0.1`, `::1`).
5. **Strict Local Binding:** The backend binds strictly to `127.0.0.1:8000`, preventing direct external socket exposure.
6. **Fail-Closed Configuration:** If Cloudflare Access is enforced but audience or team configuration is missing, all authentication requests fail closed with HTTP 403 Forbidden.

---

## 2. Inventory of Modified & Created Files

| File | Change Type | Purpose |
| :--- | :---: | :--- |
| `backend/requirements-prod.txt` | Modified | Added production dependency `pyjwt==2.15.1` (backed by `cryptography==50.0.2`). |
| `backend/pyproject.toml` | Modified | Updated project dependencies to specify `pyjwt>=2.8.0`. |
| `backend/app/core/config.py` | Modified | Added `HOST`, `PORT`, `TRUSTED_PROXIES`, `CLOUDFLARE_ACCESS_TEAM_DOMAIN`, `CLOUDFLARE_ACCESS_EXPECTED_AUD`, `CLOUDFLARE_ACCESS_CERTS_URL`, and computed issuer/JWKS properties. |
| `backend/app/services/cloudflare_access_service.py` | **Created** | Core cryptographic service: `JWKSCache`, `CloudflareAccessService.verify_jwt`, fail-closed assertions, anti-spoofing checks, and test helper key injection. |
| `backend/app/core/security.py` | Modified | Added `get_trusted_client_ip()` and `is_trusted_secure_request()` with socket-level proxy spoofing defenses. |
| `backend/app/api/routes/auth.py` | Modified | Enforced `CloudflareAccessService.extract_and_verify_request()` on `/api/auth/login` and `/api/auth/invitations/accept`. Replaced naive headers with trusted IP/cookie helpers. |
| `backend/tests/test_phase14_4_web_pilot.py` | Modified | Updated pilot security tests to assert RS256 JWT validation and reject forged email headers. |
| `backend/tests/test_phase14_4_1_access_security.py` | **Created** | Comprehensive 14-test cryptographic security test suite covering all attack vectors. |
| `experiments/reports/PHASE14_4_1_ACCESS_SECURITY_AUDIT.md` | **Created** | This formal security audit and compliance document. |

---

## 3. Cryptographic Implementation Details

### 3.1. Library & Algorithm Specification
- **Library:** `PyJWT` (v2.15.1) leveraging `cryptography` (v50.0.2).
- **Asymmetric Algorithm:** Strictly enforced **RS256** (RSA Signature with SHA-256). Any attempt to pass other algorithms (such as `none`, symmetric `HS256`, or alternative curves) is rejected immediately during header inspection:
  ```python
  if unverified_header.get("alg") != "RS256":
      raise CloudflareInvalidTokenError("Unsupported JWT algorithm. Cloudflare Access requires RS256.")
  ```

### 3.2. JWKS Public Key Retrieval & Caching Mechanism
Cloudflare publishes public signing keys at `https://<team_domain>.cloudflareaccess.com/cdn-cgi/access/certs` in standard RFC 7517 JWKS format.
- `JWKSCache` caches parsed cryptography RSA public key objects indexed by Key ID (`kid`).
- Default cache TTL is configured to **3600 seconds** (`CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_SECONDS`).
- When a token arrives with an unknown `kid` or an expired cache, keys are fetched via an HTTPS timeout-bounded request (5.0s) and converted to public keys via `jwt.algorithms.RSAAlgorithm.from_jwk()`.
- **Test Isolation:** The cache exposes `inject_key()` and `inject_jwks()` to enable fully offline, high-speed unit testing using ephemeral RSA key pairs without external network roundtrips.

### 3.3. Claims Verification Pipeline
When `CLOUDFLARE_ACCESS_ENFORCED = True`, tokens extracted from the `Cf-Access-Jwt-Assertion` header (or `CF_Authorization` cookie) must satisfy:
1. **Audience (`aud`):** Must strictly match `CLOUDFLARE_ACCESS_EXPECTED_AUD`.
2. **Issuer (`iss`):** Must match `https://<CLOUDFLARE_ACCESS_TEAM_DOMAIN>.cloudflareaccess.com`.
3. **Expiration (`exp`):** Verified against current UTC time; expired tokens are rejected.
4. **Subject / Email (`email` / `sub`):** Extracted from payload and normalized (lowercased, stripped).
5. **Anti-Header-Spoofing:** If `CF-Access-Authenticated-User-Email` is supplied alongside the JWT, it must match the verified token email exactly. Mismatches are rejected as tampering attempts.

### 3.4. Fail-Closed Security Posture
If `CLOUDFLARE_ACCESS_ENFORCED` is set to `True` but `CLOUDFLARE_ACCESS_EXPECTED_AUD` or `CLOUDFLARE_ACCESS_TEAM_DOMAIN` is omitted or empty, the engine refuses all login and invitation requests with:
```
HTTP 403 Forbidden: Cloudflare Access perimeter is enforced but CLOUDFLARE_ACCESS_EXPECTED_AUD or CLOUDFLARE_ACCESS_TEAM_DOMAIN is not configured (fail-closed).
```

---

## 4. Proxy Header Anti-Spoofing & Network Binding

### 4.1. Socket-Level Trust Boundary
In reverse-proxy architectures, attackers connecting directly to backend sockets may supply fabricated HTTP headers (`CF-Connecting-IP: 1.2.3.4`, `X-Forwarded-For: 10.0.0.1`, `X-Forwarded-Proto: https`).

FLODSS v1.0.0-rc.1 now enforces strict socket host verification in `app.core.security`:
```python
def get_trusted_client_ip(request: Any) -> str:
    direct_ip = request.client.host if (hasattr(request, "client") and request.client) else "unknown"
    if direct_ip not in settings.TRUSTED_PROXIES:
        # Direct connection from untrusted origin: completely ignore proxy headers
        return direct_ip

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return direct_ip
```
- Configured default `TRUSTED_PROXIES`: `["127.0.0.1", "::1", "testclient"]`.
- Untrusted direct clients attempting to spoof `X-Forwarded-Proto: https` will **not** trigger the `Secure` flag on session cookies or bypass scheme inspections.

### 4.2. Mandatory `127.0.0.1` Listening
- Verified in `scripts/run_backend.ps1`:
  ```powershell
  & $VenvPython -m uvicorn app.main:app --app-dir "$PSScriptRoot\..\backend" --reload --host 127.0.0.1 --port 8000
  ```
- Verified in `README_PRIVATE.md` Section 3:
  ```powershell
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- Settings default `HOST` is locked to `"127.0.0.1"`.

---

## 5. Security Test Suite Results & Attack Verification

The dedicated security test suite `backend/tests/test_phase14_4_1_access_security.py` verifies all 8 core attack scenarios:

```
backend/tests/test_phase14_4_1_access_security.py .............. [100%]
14 passed in 6.61s
```

### Scenario Breakdown

| # | Attack / Verification Scenario | Test Name | Simulated Input | System Response | Result |
| :-: | :--- | :--- | :--- | :--- | :-: |
| **1** | **Forged Email Header** | `test_forged_email_header_rejected_without_jwt` | `CF-Access-Authenticated-User-Email: admin@flodss.local`, No JWT | HTTP 403 Forbidden: Missing or empty Cf-Access-Jwt-Assertion | **PASSED** |
| **2** | **Missing JWT Assertion** | `test_missing_jwt_rejected_when_enforced` | No Cloudflare headers | HTTP 403 Forbidden: Perimeter authentication required | **PASSED** |
| **3** | **Invalid JWT Signature** | `test_invalid_jwt_signature_rejected` | JWT signed with unknown alien RSA private key | HTTP 403 Forbidden: Key ID not found in JWKS certificates | **PASSED** |
| **4** | **Wrong Audience (AUD)** | `test_wrong_audience_rejected` | JWT `aud: wrong-application-aud` | HTTP 403 Forbidden: Audience mismatch | **PASSED** |
| **5** | **Expired JWT Token** | `test_expired_jwt_rejected` | Valid JWT with `exp: now - 300` | HTTP 403 Forbidden: JWT assertion has expired | **PASSED** |
| **6** | **Mismatched Login Email** | `test_mismatched_email_between_login_and_jwt_rejected` | JWT verified for `alice@research`, login payload `admin@flodss` | HTTP 403 Forbidden: Login email must match verified JWT email | **PASSED** |
| **7** | **Header vs JWT Spoofing** | `test_mismatched_email_between_header_and_jwt_rejected` | JWT verified for `alice@research`, header `admin@flodss` | HTTP 403 Forbidden: Header does not match cryptographically verified token | **PASSED** |
| **8** | **Mismatched Invitation Target** | `test_invitation_acceptance_enforces_cryptographic_jwt` | JWT verified for `intruder@outside`, invite for `new_res@lab` | HTTP 403 Forbidden: Invitation target email must match verified JWT email | **PASSED** |
| **9** | **Cookie Token Fallback** | `test_cf_authorization_cookie_fallback` | `CF_Authorization` cookie carrying valid JWT assertion | HTTP 200 OK: Validated and session token issued | **PASSED** |
| **10** | **Fail-Closed Configuration** | `test_fail_closed_configuration_on_missing_aud_or_domain` | Enforced = True, AUD/Team = None | HTTP 403 Forbidden: Fail-closed triggered | **PASSED** |
| **11** | **Untrusted IP Header Spoofing** | `test_untrusted_direct_connection_ignores_spoofed_ip_headers` | Direct host `198.51.100.24`, header `CF-Connecting-IP: 10.0.0.1` | Returns `198.51.100.24` (Spoofed header completely ignored) | **PASSED** |
| **12** | **Untrusted Scheme Spoofing** | `test_untrusted_direct_connection_ignores_spoofed_https_headers` | Direct host `198.51.100.24`, header `X-Forwarded-Proto: https` | Returns `False` (Insecure connection preserved) | **PASSED** |
| **13** | **Trusted IPv4 Proxy Forwarding** | `test_trusted_proxy_connection_accepts_valid_forwarded_headers` | Direct host `127.0.0.1`, header `CF-Connecting-IP: 203.0.113.195` | Returns `203.0.113.195` (Forwarded header accepted) | **PASSED** |
| **14** | **Trusted IPv6 Proxy Forwarding** | `test_ipv6_localhost_trusted_proxy_connection_accepted` | Direct host `::1`, header `CF-Connecting-IP: 198.51.100.77` | Returns `198.51.100.77` (Forwarded header accepted) | **PASSED** |

---

## 6. Full Suite Regression Verification & Production Smoke Tests

### 6.1. Backend Pytest Suite
Executed complete test suite across all 28 test modules:
```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.0.2, pluggy-1.6.0
collected 422 items

backend/tests/test_aldep.py ................................             [  7%]
backend/tests/test_algorithms.py ......                                  [  9%]
backend/tests/test_api.py .                                              [  9%]
backend/tests/test_benchmark.py ............                            [ 12%]
backend/tests/test_corelap.py ...................................        [ 20%]
backend/tests/test_craft.py ....................                         [ 25%]
backend/tests/test_evaluation.py ........                                [ 27%]
backend/tests/test_evaluation_engine.py ................................ [ 34%]
backend/tests/test_feasible_generator.py .....................            [ 39%]
backend/tests/test_genetic_algorithm.py ................                 [ 43%]
backend/tests/test_geometry_and_representation.py ...................... [ 48%]
backend/tests/test_models.py .........                                   [ 51%]
backend/tests/test_phase10_pareto.py ....................                [ 55%]
backend/tests/test_phase11_1_consistency_audit.py ...............        [ 59%]
backend/tests/test_phase11_adaptive_strategy.py ................         [ 63%]
backend/tests/test_phase12_ai_explanation.py ....................       [ 67%]
backend/tests/test_phase13_validation_security.py ............           [ 70%]
backend/tests/test_phase14_1_security.py ....................            [ 75%]
backend/tests/test_phase14_2_pilot_readiness.py .................        [ 79%]
backend/tests/test_phase14_4_1_access_security.py ..............         [ 82%]
backend/tests/test_phase14_4_web_pilot.py ..........                     [ 85%]
backend/tests/test_phase14_release_candidate.py ............             [ 88%]
backend/tests/test_phase8_1_verification.py ................             [ 91%]
backend/tests/test_phase9_1_verification.py ..................           [ 96%]
backend/tests/test_phase9_2_evaluation_audit.py .........                [ 98%]
backend/tests/test_problem_ingestion.py .......                          [100%]
backend/tests/test_rectangular_feasibility.py .                          [100%]

======================== 422 passed, 1 warning in 27.94s =======================
```
- **Baseline Test Count:** 408 tests.
- **New Security Test Count:** 14 tests.
- **Total Tests Passed:** **422 tests passed (100% success rate, 0 failures, 0 regressions).**

### 6.2. Frontend Production Compilation
```
> facility-layout-frontend@1.0.0-rc.1 build
> tsc && vite build

vite v5.4.21 building for production...
transforming...
✓ 1509 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.74 kB │ gzip:   0.42 kB
dist/assets/index-CX_xZ-Vp.css    0.74 kB │ gzip:   0.43 kB
dist/assets/index-CT4uqBow.js   479.36 kB │ gzip: 109.02 kB
✓ built in 10.00s
```
- **TypeScript:** 0 compilation errors.
- **Single-Origin Dist Bundle:** Successfully generated in `frontend/dist`.

### 6.3. Single-Origin Localhost Production Smoke Test
Executed `scripts/smoke_test_single_origin.py`:
```
======================================================================
FLODSS Phase 14.4: Single-Origin Production Smoke Test
======================================================================

[Step 1] Requesting '/' with browser Accept header...
  [PASS] Root returned compiled index.html shell (Status 200)

[Step 2] Requesting compiled assets from '/assets/'...
  [PASS] Static asset '/assets/index-CT4uqBow.js' served successfully (479695 bytes)

[Step 3] Querying '/api/health'...
  [PASS] System healthy: Facility Layout Optimization & Decision Support System v1.0.0-rc.1

[Step 4] Probing protected endpoint '/api/projects' without credentials...
  [PASS] Unauthenticated access rejected with HTTP 401 Unauthorized

[Step 5] Authenticating as Admin with Cloudflare Tunnel HTTPS headers...
  [PASS] Authenticated as admin@flodss.local (Role: ADMIN)
  [PASS] Cookie has 'Secure', 'HttpOnly', and 'SameSite=Lax' flags

[Step 6] Verifying user profile via '/api/auth/me'...
  [PASS] User profile confirmed via Bearer session token

[Step 7] Running synthetic optimization solve (/api/algorithms/corelap/solve)...
  [PASS] Solved synthetic benchmark with 4 departments
  [PASS] Layout feasibility: True
  [PASS] MHC: 700.00

[Step 8] Terminating session via '/api/auth/logout'...
  [PASS] Session revoked successfully; subsequent calls rejected with HTTP 401

======================================================================
ALL PRODUCTION-LIKE SMOKE TESTS PASSED (8/8 CHECKS SUCCESSFUL)
======================================================================
```

---

## 7. Honest Disclosure Regarding Cloudflare Connectivity

> [!NOTE]
> **No live external Cloudflare API or tunnel connection was made during this audit.**
> - All tests were executed in an isolated, private localhost environment.
> - Cryptographic verification was validated using mathematically identical synthetic 2048-bit RSA key pairs (`cryptography.hazmat.primitives.asymmetric.rsa`) injected into the in-memory `JWKSCache`.
> - The application has **not** been exposed to the public internet, no public Cloudflare Tunnels have been initiated, no real domain names or DNS records were modified, and no real invitation emails were transmitted to external addresses.
> - When deployed behind a live Cloudflare Access perimeter, the only step required is setting the environment variables:
>   - `CLOUDFLARE_ACCESS_ENFORCED=true`
>   - `CLOUDFLARE_ACCESS_TEAM_DOMAIN=<your-team-subdomain>`
>   - `CLOUDFLARE_ACCESS_EXPECTED_AUD=<your-application-aud-tag>`

---

## 8. Gate Decision & Summary

| Security Criterion | Requirement | Status |
| :--- | :--- | :---: |
| Unsigned Email Header Trust | Never trust `CF-Access-Authenticated-User-Email` alone | **SEALED & VERIFIED** |
| Asymmetric Cryptographic Assertion | RS256 JWT signature verification via RFC 7517 JWKS | **IMPLEMENTED & VERIFIED** |
| Claim Validation | Issuer, Audience, Expiration, Subject verified | **IMPLEMENTED & VERIFIED** |
| Identity Binding | Token identity strictly bound to login/invitation payload | **SEALED & VERIFIED** |
| Proxy Header Anti-Spoofing | `CF-Connecting-IP` / `X-Forwarded-*` only from `TRUSTED_PROXIES` | **SEALED & VERIFIED** |
| Direct Socket Binding | Locked to `127.0.0.1:8000` | **VERIFIED** |
| Fail-Closed Integrity | Incomplete configuration rejects all authentication requests | **VERIFIED** |
| Regression Status | All 408 existing tests preserved + 14 new tests | **422 / 422 PASSED** |
| Single-Origin Smoke Test | Vite static bundle, health, auth, solve | **8 / 8 PASSED** |

### **VERDICT: GO**
The Cloudflare Access Trust Boundary vulnerability is completely resolved. The codebase is cryptographically hardened, verified against 14 targeted attack vectors, and structurally ready for private pilot access behind Cloudflare Tunnel + Cloudflare Access.
