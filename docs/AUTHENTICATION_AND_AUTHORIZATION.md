# FLODSS — Authentication & Role-Based Authorization Architecture (Phase 14.1)

## 1. Executive Summary

FLODSS (Facility Layout Optimization Decision Support System) v1.0.0-rc.1 implements a **Controlled Research Access** architecture designed specifically for academic thesis research, laboratory evaluations, and closed pilot studies. 

The system operates strictly **local-first** and **closed-source**, preventing public registration, unauthorized data access, and third-party data leakage while enforcing strict cryptographic guarantees for user authentication and authorization.

---

## 2. Authentication Mechanics

### 2.1 Password Security & Cryptographic Hashing
- **Algorithm**: PBKDF2 (Password-Based Key Derivation Function 2) using HMAC-SHA-256.
- **Iteration Count**: **600,000 iterations** (exceeding OWASP 2024 recommendations of 600,000 iterations for PBKDF2-HMAC-SHA256).
- **Salt Generation**: 16 cryptographically secure random bytes generated via `secrets.token_bytes(16)`.
- **Storage Format**: Hex-encoded salt and derived key formatted as `salt$hash` (`backend/app/core/security.py`).
- **Timing Attack Resistance**: Password verification uses constant-time string comparison (`hmac.compare_digest`).

### 2.2 Token Architecture & Session Management
- **Token Format**: 32 cryptographically secure random bytes (256-bit entropy) generated using `secrets.token_urlsafe(32)`.
- **Session Duration**: Tokens expire after **24 hours** (`SESSION_EXPIRY_HOURS = 24`).
- **Storage**: Persistent SQLite session records (`sessions` table) storing:
  - `session_token`: Unique bearer token.
  - `user_id`: Foreign key reference to active user.
  - `created_at`: UTC timestamp of authentication.
  - `expires_at`: UTC timestamp of session expiration.
  - `last_activity_at`: Updated on authenticated requests.
- **Revocation**:
  - Explicit sign-out immediately deletes session from the database.
  - Disabling a user account (`is_active = FALSE`) instantly revokes all active sessions.

### 2.3 Invitation-Only User Onboarding
- **Strict Invite-Only Policy**: Public registration (`/register`) is completely disabled. Users can only join if invited by an `ADMIN`.
- **Invitation Token**: 32-byte URL-safe cryptographically secure token (`secrets.token_urlsafe(32)`).
- **Invitation Validity**: **48 hours** (`INVITATION_EXPIRY_HOURS = 48`). Single-use only.
- **Redemption Workflow**:
  1. Administrator generates invitation specifying email and target role (`ADMIN`, `RESEARCHER`, `VIEWER`).
  2. The candidate receives the token securely through institutional channels.
  3. The candidate redeems the token via `/api/auth/invitations/accept`, providing full name and password.
  4. The system creates the user record, marks the invitation as used (`used_at` timestamp), and issues a session token.

---

## 3. Role-Based Access Control (RBAC)

FLODSS defines a 3-tier role hierarchy:

| Role | Permissions & Scope |
| :--- | :--- |
| **`ADMIN`** | • Full system administration.<br>• Generate and revoke invitations.<br>• View all registered users and toggle active/disabled status.<br>• Grant/revoke Gemini AI reasoning privileges.<br>• View system-wide audit logs.<br>• Execute all optimization algorithms.<br>• Create, edit, and export research projects and layout benchmarks. |
| **`RESEARCHER`** | • Create and manage own research projects.<br>• Upload custom problem definitions and facility geometries.<br>• Run heuristic, metaheuristic, and multi-objective solvers.<br>• Execute Pareto frontier and trade-off analysis.<br>• Archive and retrieve immutable experiment runs.<br>• Use Gemini AI decision explanations (if consent granted and enabled by Admin).<br>• Cannot manage users or view projects belonging to other researchers. |
| **`VIEWER`** | • Read-only inspection of shared projects and benchmark datasets.<br>• Interactive 2D layout canvas navigation and zoom.<br>• View evaluation metrics, Pareto charts, and algorithm comparison summaries.<br>• Cannot trigger optimization solvers (computational endpoints return HTTP 403 Forbidden).<br>• Cannot modify problem configurations or save new experiment runs. |

### Role Enforcement Matrix

| Endpoint / Operation | ADMIN | RESEARCHER | VIEWER | Unauthenticated |
| :--- | :---: | :---: | :---: | :---: |
| `POST /api/auth/invitations` | ✅ | ❌ (403) | ❌ (403) | ❌ (401) |
| `GET /api/auth/users` | ✅ | ❌ (403) | ❌ (403) | ❌ (401) |
| `PATCH /api/auth/users/{id}/status` | ✅ | ❌ (403) | ❌ (403) | ❌ (401) |
| `POST /api/projects` | ✅ | ✅ | ❌ (403) | ❌ (401) |
| `POST /api/algorithms/run` | ✅ | ✅ | ❌ (403) | ❌ (401) |
| `POST /api/adaptive/solve` | ✅ | ✅ | ❌ (403) | ❌ (401) |
| `GET /api/projects/{id}` (own project) | ✅ | ✅ | ✅ | ❌ (401) |
| `GET /api/projects/{id}` (other's project) | ✅ | ❌ (404/403) | ❌ (404/403) | ❌ (401) |
| `GET /api/experiments/{id}` (own experiment) | ✅ | ✅ | ✅ | ❌ (401) |
| `POST /api/ai/consent` | ✅ | ✅ | ❌ (403) | ❌ (401) |

---

## 4. Rate Limiting & Resource Protection

### 4.1 In-Memory Sliding-Window Rate Limiter
- **Login Rate Limit**: Max 5 attempts per minute per IP address (`/api/auth/login`).
- **Invitation Creation Limit**: Max 10 attempts per minute per IP address.
- **Implementation**: `SlidingWindowRateLimiter` using deque-based sliding window timestamps (`backend/app/core/security.py`).
- **Response**: HTTP 429 Too Many Requests with retry advisory headers.

### 4.2 Job Concurrency Management
- **Global Concurrency Limit**: Maximum **2 concurrent optimization jobs** globally (`MAX_CONCURRENT_JOBS = 2`).
- **Per-User Concurrency Limit**: Maximum **1 active job per user** (`MAX_USER_CONCURRENT_JOBS = 1`).
- **Implementation**: `JobConcurrencyManager` with async slot acquisition and release guards (`JobSlotGuard`).
- **Response**: HTTP 429 Too Many Requests with informative error message advising queue drain.

### 4.3 Upload & Payload Limiting
- **Max Payload Size**: 10 Megabytes (`MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024`).
- **Middleware**: `limit_upload_size` inspecting `Content-Length` header; returns HTTP 413 Payload Too Large.

---

## 5. Security Headers
All HTTP responses include security hardening headers:
- `X-Content-Type-Options: nosniff` (MIME sniffing prevention)
- `X-Frame-Options: DENY` (Clickjacking prevention)
- `Referrer-Policy: strict-origin-when-cross-origin` (Privacy and leak prevention)
