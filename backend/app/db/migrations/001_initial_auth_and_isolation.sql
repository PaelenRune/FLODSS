-- ==============================================================================
-- FLODSS Phase 14.1: Controlled Research Access & User Data Isolation Schema
-- Compatible with SQLite 3 and PostgreSQL 14+
-- ==============================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'RESEARCHER', 'VIEWER')),
    is_active INTEGER NOT NULL DEFAULT 1,
    allow_gemini INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. Invitations Table (Expiring, Single-Use Tokens)
CREATE TABLE IF NOT EXISTS invitations (
    id TEXT PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'RESEARCHER', 'VIEWER')),
    created_by_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);

-- 3. Sessions Table (Server-side Session Management)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    token_hash TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- 4. Research Projects Table (Data Isolation Boundary)
CREATE TABLE IF NOT EXISTS research_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON research_projects(owner_user_id);

-- 5. Access Grants Table (Role-based & Project-level Authorization)
CREATE TABLE IF NOT EXISTS access_grants (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    permission TEXT NOT NULL CHECK (permission IN ('VIEW', 'EDIT', 'ADMIN')),
    granted_by_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES research_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_grants_project ON access_grants(project_id);
CREATE INDEX IF NOT EXISTS idx_grants_user ON access_grants(user_id);

-- 6. Facility Problems Table (Custom & Benchmark Problems within Projects)
CREATE TABLE IF NOT EXISTS facility_problems (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    problem_hash TEXT NOT NULL,
    facility_data TEXT NOT NULL,
    owner_user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES research_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_problems_project ON facility_problems(project_id);

-- 7. Optimization Runs Table (Immutable Reproducible Experiment Logs)
CREATE TABLE IF NOT EXISTS optimization_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    algorithm_name TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    flodss_version TEXT NOT NULL,
    parameters TEXT NOT NULL,
    random_seed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    termination_reason TEXT,
    runtime_ms REAL NOT NULL,
    problem_hash TEXT NOT NULL,
    evaluation_config_hash TEXT NOT NULL,
    layout_signature TEXT,
    is_feasible INTEGER NOT NULL,
    canonical_metrics TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES research_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON optimization_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_user ON optimization_runs(user_id);

-- 8. Candidate Layouts Table
CREATE TABLE IF NOT EXISTS candidate_layouts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    layout_signature TEXT NOT NULL,
    layout_data TEXT NOT NULL,
    is_pareto_optimal INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES optimization_runs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_candidates_run ON candidate_layouts(run_id);

-- 9. Evaluation Results Table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    layout_signature TEXT NOT NULL,
    report_data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES optimization_runs(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_eval_results_run ON evaluation_results(run_id);

-- 10. Audit Events Table (Security & Confidentiality Trail)
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    ip_address TEXT,
    details TEXT,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
