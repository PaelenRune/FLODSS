# FLODSS — Private Pilot Operations Manual (Phase 14.2)

## 1. Scope, Purpose & Confidentiality Boundaries

FLODSS (Facility Layout Optimization Decision Support System) v1.0.0-rc.1 is an advanced operations research and industrial engineering platform designed for academic thesis evaluations, doctoral research, and closed laboratory pilots.

### 1.1 Confidentiality Directives
- **Zero Public Exposure**: FLODSS must NEVER be deployed to public internet hosts, registered under public DNS domains, or bridged through public reverse tunnels (e.g., ngrok, localtunnel).
- **No Public Code Repositories**: Source code, problem definitions, and database artifacts must remain strictly confidential on internal departmental workstations.
- **AI Dual Opt-in**: External Gemini AI reasoning is disabled by default (`AI_ENABLED=false`). When enabled, it requires explicit Administrative permission AND runtime per-session researcher consent. No confidential factory data is transmitted without explicit user confirmation.

---

## 2. Infrastructure & Local-First Deployment

FLODSS operates in a **local-first, multi-tenant** architecture on a departmental research workstation or lab server:

```
[ Research Workstation / Lab Server ]
├── Backend: FastAPI 0.115+ (Python 3.12+) on 127.0.0.1:8000
│   ├── NumPy / SciPy / Pydantic v2
│   ├── PBKDF2-HMAC-SHA256 (600,000 iterations)
│   ├── Sliding-window Rate Limiter & Concurrency Manager
│   └── SQLite 3 (WAL mode, Foreign Keys ON) at data/flodss_research.db
└── Frontend: React 18 / TypeScript / Vite on 127.0.0.1:5173
    └── Production Build: dist/ (Zero external CDN dependencies)
```

### 2.1 Starting the System
1. **Backend Server**:
   ```powershell
   cd backend
   .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --host 127.0.0.1
   ```
2. **Frontend Interface**:
   ```powershell
   cd frontend
   npm.cmd run dev -- --port 5173 --host 127.0.0.1
   ```
3. Open browser at `http://127.0.0.1:5173`.

---

## 3. Administrator Governance & User Onboarding

### 3.1 Initial Administrator Access
- **Email**: `admin@flodss.local`
- **Initial Password**: `FlodssAdmin2026!`
- **Role**: `ADMIN`

### 3.2 Generating Invitations for Pilot Participants
1. In the top navigation bar, click the **👥 Users** button.
2. In the modal, select the **+ Issue New Invitation** tab.
3. Enter the candidate's institutional email address (e.g., `advisor@university.edu`) and target role:
   - `RESEARCHER`: Can create projects, edit problems, execute solvers, and archive runs.
   - `VIEWER`: Read-only observer; cannot trigger solvers or modify data.
4. Click **Generate 48h Invitation Token**.
5. Copy the generated secret token (e.g., `CwADhmEKkYworita...`) and securely deliver it to the invitee.

### 3.3 Account Status & AI Privilege Governance
In the **Registered Users** tab, the Administrator can:
- **Enable / Disable Account**: Disabling a researcher instantly revokes all active session tokens and blocks subsequent logins.
- **Grant / Revoke AI Privileges**: Controls whether the researcher is allowed to use Gemini AI decision explanations.

---

## 4. End-to-End Researcher User Acceptance Flow

Non-technical researchers and thesis advisors can complete a full optimization experiment using the following 9-step workflow:

1. **Accept Invitation**:
   - Navigate to `http://127.0.0.1:5173`.
   - Click **"Have an invitation token? Activate your account"**.
   - Paste the token and click **Verify Token & Proceed**.
   - Enter full academic title (e.g., `Prof. Jane Doe, Ph.D.`) and set password (min 8 chars).
   - Click **Complete Activation & Enter Workspace**.
2. **Sign In**:
   - Enter registered institutional email and password to access the workspace.
3. **Select Factory Benchmark Problem**:
   - In **Tab 1 (Problem Editor)**, select `FLP_INDUSTRIAL_10` from the benchmark dropdown.
   - Review facility dimensions ($150\text{ m} \times 80\text{ m}$) and 10 manufacturing departments.
4. **Inspect Factory Data**:
   - Inspect department area constraints, fixed positions, and aspect ratio bounds.
   - Switch to **Tab 2 (Flow & REL)** to inspect material flow intensities and REL closeness ratings.
5. **Execute Adaptive Mode Solver**:
   - Switch to **Tab 4 (Optimization)**.
   - Select **Adaptive Strategy Engine** (or GA / CRAFT / Guillotine).
   - Click **⚡ Run Adaptive Strategy**.
   - Watch the execution status bar complete with wall-clock time recording.
6. **Inspect 2D Floor Plan Layout**:
   - Switch to **Tab 5 (2D Layout Viewer)**.
   - Navigate the interactive canvas (Zoom, Pan, Centroids, Dimensions).
   - Verify that all departments are within facility boundaries with zero pairwise overlap.
7. **Evaluate Objectives & Pareto Trade-Offs**:
   - Switch to **Tab 6 (Pareto & Trade-offs)**.
   - Review Material Handling Cost (MHC), Relationship Satisfaction percentage, and Soft Penalties.
8. **Save Experiment**:
   - At the top of the screen in the **Active Research Project** card, click **💾 Save Current Run**.
   - Verify that the run appears in the **Project Experiment History** table.
9. **Download Deliverables (CSV & SVG)**:
   - Switch to **Tab 8 (Export Center)**.
   - Click **Download Metrics CSV** for numerical analysis.
   - Click **Download Layout SVG** for vector graphics reporting in thesis LaTeX/Word documents.

---

## 5. Security Architecture & Multi-Tenant Boundaries

| Layer | Security Mechanism |
| :--- | :--- |
| **Password Storage** | PBKDF2-HMAC-SHA256 with 600,000 iterations and 32-byte cryptographically secure random salt. |
| **Session Tokens** | 256-bit URL-safe bearer tokens hashed with SHA-256 at rest in the database. |
| **Tenant Isolation** | All project and experiment queries strictly enforce `owner_user_id = current_user.id`. |
| **IDOR Defense** | Cross-tenant requests to `/api/projects/{id}` or `/api/experiments/{id}` return HTTP 403 Forbidden. |
| **Session Invalidation** | Explicit logout or administrative account deactivation immediately revokes active bearer tokens. |
| **Rate Limiting** | Sliding-window limiter on login (max 5 attempts/minute/IP) with automatic reset. |
| **Job Concurrency** | Global limit of 2 concurrent solver jobs; max 1 job per user. |
| **Payload Clamping** | Maximum 10 MB request payload enforced at middleware layer (HTTP 413). |
| **Security Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. |

---

## 6. Database Maintenance & Backup Protocol

### 6.1 Creating a Live Database Backup
Execute the online backup utility (non-blocking via SQLite Online Backup API):
```powershell
python scripts/backup_and_restore.py backup
```
The utility generates an integrity-verified snapshot under `data/backups/flodss_backup_<timestamp>.db`.

### 6.2 Restoring from Backup
```powershell
python scripts/backup_and_restore.py restore data/backups/flodss_backup_<timestamp>.db
```
The utility validates `PRAGMA integrity_check;` on the backup file before restoring it to `data/flodss_research.db`.

### 6.3 SQLite Suitability vs Multi-Node Production
- **Localhost Pilot Suitability**: SQLite in Write-Ahead Logging (WAL) mode with a 30-second busy timeout is ideal for local, single-server pilots with 5-15 concurrent research users.
- **Production Enterprise Transition**: If FLODSS is ever transitioned to a distributed multi-node production deployment in future phases, the data layer can be migrated to PostgreSQL via the existing ANSI-compatible migration schemas.
