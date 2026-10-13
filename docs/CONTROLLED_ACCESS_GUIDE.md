# FLODSS — Controlled Research Access Operator Guide (Phase 14.1)

## 1. Introduction & Research Protocol

FLODSS v1.0.0-rc.1 is configured as a **controlled-access, local-first research platform**. It is designed to facilitate confidential academic thesis research, doctoral evaluations, and peer-reviewed algorithmic benchmarks without exposing intellectual property or research data to external networks.

This manual instructs Thesis Advisors, Principal Investigators (PIs), and Research Administrators on deploying, administering, and operating FLODSS.

---

## 2. Administrator Bootstrap & First Login

### 2.1 Default Credentials
On initial startup, FLODSS automatically creates the master research administrator account if no admin exists:
- **Email**: `admin@flodss.local`
- **Initial Password**: `FlodssAdmin2026!`
- **Role**: `ADMIN`
- **Database**: `data/flodss_research.db`

> **Note**: For production evaluations, the administrator must change their password or update the default admin password in `backend/app/core/config.py` (`DEFAULT_ADMIN_PASSWORD`).

### 2.2 Logging In
1. Open a web browser and navigate to the local research instance (default: `http://localhost:5173` or `http://127.0.0.1:8000`).
2. The **FLODSS Research Portal** login dialog will appear automatically.
3. Enter `admin@flodss.local` and your password.
4. Upon successful authentication, your name (`Lead Research Administrator`) and the red `ADMIN` role badge will appear in the top-right header.

---

## 3. Inviting Thesis Advisors & Pilot Researchers

FLODSS uses a **strict invitation-only model**. Public self-registration is permanently disabled.

### 3.1 Generating an Invitation Token
1. In the top navigation header, click the **👥 Users** button (visible only to `ADMIN`).
2. In the **User & Access Management** panel, navigate to the **Generate Single-Use Research Invitation** form.
3. Complete the invitation parameters:
   - **Invitee Email**: Institutional email of the researcher (e.g., `advisor@university.edu`).
   - **Target Role**: Select `RESEARCHER` (can create projects and run solvers) or `VIEWER` (read-only inspection).
   - **Validity**: Tokens automatically expire **48 hours** from issuance.
4. Click **Generate Single-Use Invitation**.
5. The generated token (e.g., `dLcSisOOAPerWkdBdinB3B8Fq50GIyZFGitJ870pCWE`) and copyable onboarding link will be displayed:
   ```
   http://localhost:5173/?invite=dLcSisOOAPerWkdBdinB3B8Fq50GIyZFGitJ870pCWE
   ```

### 3.2 Secure Token Delivery
Deliver the token or direct link to the invited researcher via secure institutional email or encrypted departmental messaging.

---

## 4. Researcher Onboarding Flow

When the invited candidate accesses FLODSS:
1. On the login dialog, click **"Have an invitation token? Activate your account"**.
2. Paste the 40+ character invitation token into the verification input and click **Verify Token & Proceed**.
3. FLODSS verifies token authenticity, remaining validity time, and assigned role.
4. Enter your **Full Name & Academic Title** (e.g., `Dr. Jane Doe, Associate Professor`).
5. Set a secure password (minimum 8 characters) and confirm it.
6. Click **Complete Activation & Enter Workspace**.
7. The account is immediately created, the invitation is permanently invalidated, a default research project is provisioned, and the researcher is transitioned into the workspace with the blue `RESEARCHER` badge.

---

## 5. Research Project Management & Experiment Persistence

### 5.1 Project Isolation
Every researcher works within isolated project containers. Researchers cannot view or alter projects created by other researchers.

- **Creating a Project**: In the **Active Research Project** card at the top of the workspace, select **+ New Project**. Enter a project title (e.g., `Automotive Line 2 Expansion`) and click **Create**.
- **Switching Projects**: Use the project dropdown selector to switch between active research studies.

### 5.2 Archiving Reproducible Experiment Runs
When an optimization algorithm is executed in **Tab 4 (Optimization)**:
1. The solver calculates candidate layouts and canonical metrics (MHC, Flow-Distance, Rel Satisfaction, Soft Penalty).
2. The researcher clicks **💾 Save Current Run** in the Project Manager Card.
3. FLODSS saves an **immutable snapshot** to the `optimization_runs` database table:
   - Complete algorithmic hyperparameter configuration.
   - Deterministic random seed and execution duration.
   - Exact continuous coordinates of all facility departments.
   - Evaluation metrics verified by `CanonicalEvaluationService`.
4. The saved run appears in the **Experiment Runs History** table with an immutable timestamp and status badge.

---

## 6. User Governance & Access Revocation

Administrators maintain real-time governance over all users in the **👥 Users** modal:

### 6.1 Disabling a User Account
If a researcher leaves the project or thesis defense concludes:
1. Open the **👥 Users** modal.
2. Locate the user in the Registered Researchers table.
3. Click **Deactivate**.
4. The user's status immediately switches to `Disabled`.
5. **Immediate Revocation**: All active session tokens for that user are immediately invalidated, blocking further API requests and denying future login attempts.

### 6.2 Managing Gemini AI Privileges
By default, external AI reasoning is disabled (`can_use_gemini = False`). 
- To permit a researcher to use Gemini explanations, the Administrator toggles **Enable AI** for that user.
- The researcher must additionally provide runtime explicit consent (`AI Consent Modal`) before any prompt is processed.
