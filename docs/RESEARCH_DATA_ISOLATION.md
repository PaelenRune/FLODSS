# FLODSS — Research Data Isolation & Experiment Reproducibility (Phase 14.1)

## 1. Multi-Tenant Architecture & Research Boundaries

FLODSS provides an isolated workspace model tailored to academic institutions, research laboratories, and thesis committees. While operating on a single host machine or local research server, the platform strictly segregates data between participating researchers.

```
+-----------------------------------------------------------------------------------+
|                                 ADMINISTRATOR                                     |
|  • Full visibility across all research projects, users, invitations, & audit logs |
+-----------------------------------------+-----------------------------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
+---------------v---------------+                   +---------------v---------------+
|    RESEARCHER A (Pilot A)     |                   |    RESEARCHER B (Pilot B)     |
|  • Project Alpha              |                   |  • Project Beta               |
|    - Industrial 10 Benchmark  |                   |    - High Density 15 Case     |
|    - Run #1 (Adaptive)        |                   |    - Run #1 (Genetic)         |
|    - Run #2 (CRAFT)           |                   |    - Run #2 (Guillotine)      |
+-------------------------------+                   +-------------------------------+
```

---

## 2. Relational Database Schema (`data/flodss_research.db`)

The local persistence layer uses SQLite with **Write-Ahead Logging (WAL)** and strictly enforced **foreign key constraints** (`PRAGMA foreign_keys = ON;`).

### 2.1 Core Schema Entities

#### `users`
- `id` (TEXT PRIMARY KEY, UUIDv4): Unique user identifier.
- `email` (TEXT UNIQUE NOT NULL): Institutional email address.
- `full_name` (TEXT NOT NULL): Researcher or advisor full name and title.
- `password_hash` (TEXT NOT NULL): PBKDF2-HMAC-SHA256 hash (600,000 iterations).
- `role` (TEXT NOT NULL): `ADMIN`, `RESEARCHER`, or `VIEWER`.
- `is_active` (BOOLEAN NOT NULL DEFAULT 1): Active status flag.
- `can_use_gemini` (BOOLEAN NOT NULL DEFAULT 0): Explicit AI consent privilege.
- `created_at` (TIMESTAMP): Creation date.
- `updated_at` (TIMESTAMP): Last update date.

#### `invitations`
- `id` (TEXT PRIMARY KEY, UUIDv4): Unique record identifier.
- `token` (TEXT UNIQUE NOT NULL): 32-byte cryptographically secure token.
- `email` (TEXT NOT NULL): Target invitee email.
- `role` (TEXT NOT NULL): Pre-assigned role (`ADMIN`, `RESEARCHER`, `VIEWER`).
- `created_by_user_id` (TEXT NOT NULL, FK -> `users.id`): Issuing administrator.
- `expires_at` (TIMESTAMP NOT NULL): Expiration boundary (48 hours from issuance).
- `used_at` (TIMESTAMP): Timestamp of redemption (NULL if unused).

#### `sessions`
- `id` (TEXT PRIMARY KEY, UUIDv4): Session record identifier.
- `session_token` (TEXT UNIQUE NOT NULL): 256-bit bearer token.
- `user_id` (TEXT NOT NULL, FK -> `users.id` ON DELETE CASCADE): Authenticated user.
- `created_at` (TIMESTAMP NOT NULL): Login timestamp.
- `expires_at` (TIMESTAMP NOT NULL): Session expiration (24 hours).
- `last_activity_at` (TIMESTAMP NOT NULL): Activity tracker.

#### `projects`
- `id` (TEXT PRIMARY KEY, UUIDv4): Unique research project identifier.
- `name` (TEXT NOT NULL): Project name (e.g., "MSc Thesis - Line 4 Layout").
- `description` (TEXT): Scope and problem formulation details.
- `owner_user_id` (TEXT NOT NULL, FK -> `users.id` ON DELETE CASCADE): Project owner.
- `created_at` (TIMESTAMP NOT NULL): Project creation timestamp.
- `updated_at` (TIMESTAMP NOT NULL): Last project modification.

#### `project_problems`
- `id` (TEXT PRIMARY KEY, UUIDv4): Attached problem identifier.
- `project_id` (TEXT NOT NULL, FK -> `projects.id` ON DELETE CASCADE): Parent project.
- `problem_id` (TEXT NOT NULL): Canonical problem ID (e.g., `FLP_INDUSTRIAL_10`).
- `problem_name` (TEXT NOT NULL): Problem label.
- `problem_data` (TEXT NOT NULL): JSON serialized `FacilityLayoutProblem`.
- `created_by_user_id` (TEXT NOT NULL, FK -> `users.id`): Author.
- `created_at` (TIMESTAMP NOT NULL): Attachment date.

#### `optimization_runs` (Immutable Research Artifacts)
- `id` (TEXT PRIMARY KEY, UUIDv4): Unique experiment run ID.
- `project_id` (TEXT NOT NULL, FK -> `projects.id` ON DELETE CASCADE): Parent project.
- `problem_id` (TEXT NOT NULL): Solved problem identifier.
- `algorithm` (TEXT NOT NULL): Algorithm name (`Adaptive Strategy`, `Genetic Layout Algorithm`, etc.).
- `execution_status` (TEXT NOT NULL): Execution outcome (`OPTIMAL`, `FEASIBLE`, `TERMINATED`).
- `parameters` (TEXT NOT NULL): Complete JSON dictionary of execution parameters, seeds, and time limits.
- `metrics` (TEXT NOT NULL): Verified metrics JSON (MHC, Flow-Distance, REL Satisfaction, Soft Penalty, Wall-clock duration).
- `layout_data` (TEXT NOT NULL): Full JSON serialized continuous layout coordinates (`ContinuousLayout`).
- `created_by_user_id` (TEXT NOT NULL, FK -> `users.id`): Run executor.
- `created_at` (TIMESTAMP NOT NULL): Run timestamp.

#### `audit_logs`
- `id` (TEXT PRIMARY KEY, UUIDv4): Audit entry identifier.
- `user_id` (TEXT, FK -> `users.id`): Actor (nullable for anonymous actions).
- `action` (TEXT NOT NULL): Categorized event (`LOGIN_SUCCESS`, `CREATE_PROJECT`, `RUN_EXPERIMENT`).
- `resource_type` (TEXT): Entity category (`PROJECT`, `EXPERIMENT`, `INVITATION`).
- `resource_id` (TEXT): Entity ID.
- `details` (TEXT): JSON context metadata.
- `ip_address` (TEXT): Client network IP address.
- `created_at` (TIMESTAMP NOT NULL): Event timestamp.

---

## 3. IDOR / BOLA Prevention Architecture

Insecure Direct Object Reference (IDOR) and Broken Object Level Authorization (BOLA) vulnerabilities are systematically prevented at the database and service layers:

### 3.1 Project-Level Isolation
Every query accessing projects or project-scoped entities enforces explicit ownership:
```python
# backend/app/services/project_service.py
if user.role == "ADMIN":
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
else:
    cursor.execute("SELECT * FROM projects WHERE id = ? AND owner_user_id = ?", (project_id, user.id))
```
If a researcher attempts to inspect or mutate another user's project, the system raises an HTTP 404 / 403 response without leaking metadata.

### 3.2 Experiment-Level IDOR Guard
When accessing an optimization run directly via `/api/experiments/{run_id}`:
1. The service queries the run record and resolves its `project_id`.
2. It fetches the parent project and verifies that `project.owner_user_id == current_user.id` (or `current_user.role == 'ADMIN'`).
3. If unauthorized, access is denied immediately with HTTP 403 Forbidden.

---

## 4. Immutable Experiment Persistence & Reproducibility

To satisfy scientific peer-review and academic verification criteria:
1. **Append-Only Run Records**: Optimization run records are strictly immutable. There is no update or overwrite endpoint for `optimization_runs`.
2. **Deterministic Inputs**: The full configuration parameters, random seed, problem fingerprint, and environment version are archived alongside the resulting coordinates.
3. **Canonical Verification**: Every saved run includes the exact output of `CanonicalEvaluationService`, ensuring zero metric drift between execution and retrospective reporting.
