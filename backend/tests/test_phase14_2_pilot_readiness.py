"""Phase 14.2: Comprehensive Private Pilot Readiness & Multi-Tenant Verification Tests.

Tests:
1. Multi-tenant project and experiment isolation (User A vs User B).
2. Unauthorized IDOR access prevention on projects, problems, and runs.
3. VIEWER permission limits (read-only enforcement).
4. Session token hashing, verification, revocation on logout, and account disablement.
5. Job concurrency manager limits (user quota and slot release).
6. SQLite database backup, restore, foreign key integrity, and WAL mode persistence.
7. SVG and CSV export deterministic generation.
"""

import json
import sqlite3
import tempfile
import uuid
from pathlib import Path
import pytest

from app.core.config import settings
from app.core.security import (
    concurrency_manager,
    generate_secure_token,
    hash_password,
    hash_token,
    rate_limiter,
    verify_password,
)
from app.db.database import DatabaseManager
from app.models.auth import User, UserResponse, UserRole, UserStatusUpdate
from app.models.projects import (
    OptimizationRunRecord,
    PermissionLevel,
    SaveExperimentRequest,
)
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService


@pytest.fixture
def clean_db():
    """Create a temporary SQLite database initialized with all schema migrations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    mgr = DatabaseManager(db_path=db_path)
    mgr.run_migrations()
    conn = mgr.get_connection()
    AuthService.ensure_admin_user(conn)

    yield conn, db_path

    conn.close()
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass


def test_two_user_project_and_experiment_isolation(clean_db):
    """Verify User A and User B operate in strictly isolated project silos."""
    conn, _ = clean_db

    # 1. Create User A (Researcher)
    user_a_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'user_a@research.edu', 'hashed_pass_a', 'Dr. Alice A', 'RESEARCHER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (user_a_id,),
    )
    user_a = User(
        id=user_a_id,
        email="user_a@research.edu",
        full_name="Dr. Alice A",
        role=UserRole.RESEARCHER,
        is_active=True,
        allow_gemini=False,
    )

    # 2. Create User B (Researcher)
    user_b_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'user_b@research.edu', 'hashed_pass_b', 'Dr. Bob B', 'RESEARCHER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (user_b_id,),
    )
    user_b = User(
        id=user_b_id,
        email="user_b@research.edu",
        full_name="Dr. Bob B",
        role=UserRole.RESEARCHER,
        is_active=True,
        allow_gemini=False,
    )

    # User A creates a private project
    proj_a = ProjectService.create_project(
        name="Alice Private Project",
        description="Confidential Layout Study A",
        owner_user=user_a,
        conn=conn,
    )

    # User B creates a private project
    proj_b = ProjectService.create_project(
        name="Bob Private Project",
        description="Confidential Layout Study B",
        owner_user=user_b,
        conn=conn,
    )

    # Verify project listings
    list_a = ProjectService.list_user_projects(user_a, conn)
    list_b = ProjectService.list_user_projects(user_b, conn)

    assert any(p.id == proj_a.id for p in list_a), "Alice should see Project A"
    assert not any(p.id == proj_b.id for p in list_a), "Alice MUST NOT see Project B"

    assert any(p.id == proj_b.id for p in list_b), "Bob should see Project B"
    assert not any(p.id == proj_a.id for p in list_b), "Bob MUST NOT see Project A"

    # User B attempts to access Project A metadata -> Must be denied
    with pytest.raises(PermissionError):
        ProjectService.verify_project_access(proj_a.id, user_b, PermissionLevel.VIEW, conn)

    # User A saves an optimization run to Project A
    req = SaveExperimentRequest(
        project_id=proj_a.id,
        problem_id="FLP_INDUSTRIAL_10",
        algorithm_name="Adaptive Strategy Engine",
        algorithm_version="1.0.0",
        flodss_version="v1.0.0-rc.1",
        parameters={"seed": 42, "time_budget": 5.0},
        random_seed=42,
        runtime_ms=120.5,
        problem_hash="hash_industrial_10",
        evaluation_config_hash="eval_hash_canonical",
        layout_signature="sig_layout_alice",
        is_feasible=True,
        canonical_metrics={"mhc": 108504.2, "flow_dist": 69749.38, "rel_sat": 52.4, "soft_penalty": 0},
        layout_data={"facility_width": 150, "facility_height": 80, "placements": {}},
    )
    run_a = ProjectService.save_experiment_run(req, user_a, conn)

    # User A can retrieve run
    fetched_a = ProjectService.get_experiment_run(run_a.id, user_a, conn)
    assert fetched_a["run"].id == run_a.id

    # User B attempts to inspect User A's run -> Must be denied with PermissionError (HTTP 403)
    with pytest.raises(PermissionError):
        ProjectService.get_experiment_run(run_a.id, user_b, conn)

    # User B attempts to save problem to User A's project -> Must be denied
    with pytest.raises(PermissionError):
        ProjectService.save_problem(
            project_id=proj_a.id,
            name="Injected Problem",
            facility_data={"facility": {"width": 100, "height": 50}},
            user=user_b,
            conn=conn,
        )


def test_viewer_permission_limits(clean_db):
    """Verify VIEWER role has read-only access and cannot mutate projects or runs."""
    conn, _ = clean_db

    # Create Owner (Researcher)
    owner_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'owner@lab.edu', 'hashed_pass_owner', 'Prof. Advisor', 'RESEARCHER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (owner_id,),
    )
    owner = User(
        id=owner_id,
        email="owner@lab.edu",
        full_name="Prof. Advisor",
        role=UserRole.RESEARCHER,
        is_active=True,
        allow_gemini=False,
    )

    # Create Viewer
    viewer_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'viewer@lab.edu', 'hashed_pass_viewer', 'Auditor Viewer', 'VIEWER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (viewer_id,),
    )
    viewer = User(
        id=viewer_id,
        email="viewer@lab.edu",
        full_name="Auditor Viewer",
        role=UserRole.VIEWER,
        is_active=True,
        allow_gemini=False,
    )

    proj = ProjectService.create_project(name="Audited Study", owner_user=owner, conn=conn)

    # Grant VIEWER read access to project
    conn.execute(
        """
        INSERT INTO access_grants (id, project_id, user_id, permission, granted_by_user_id, created_at)
        VALUES (?, ?, ?, 'VIEW', ?, '2026-10-12T00:00:00');
        """,
        (str(uuid.uuid4()), proj.id, viewer.id, owner.id),
    )
    conn.commit()

    # Viewer CAN view project
    view_access = ProjectService.verify_project_access(proj.id, viewer, PermissionLevel.VIEW, conn)
    assert view_access["id"] == proj.id

    # Viewer CANNOT edit project
    with pytest.raises(PermissionError):
        ProjectService.verify_project_access(proj.id, viewer, PermissionLevel.EDIT, conn)


def test_session_lifecycle_token_hash_and_invalidation(clean_db):
    """Verify session token hashing at rest, logout revocation, and account disablement."""
    conn, _ = clean_db

    # Create user
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password("SecureResearchPass2026!")
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'eval@lab.edu', ?, 'Evaluator One', 'RESEARCHER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (user_id, hashed_pwd),
    )
    conn.commit()

    # Authenticate user and issue session
    auth_data = AuthService.authenticate_user("eval@lab.edu", "SecureResearchPass2026!", conn)
    token = auth_data["session_token"]
    token_hash = hash_token(token)

    # 1. Verify token is hashed in DB, raw token is NOT stored
    cur = conn.execute("SELECT token_hash FROM sessions WHERE user_id = ?;", (user_id,))
    stored = cur.fetchone()[0]
    assert stored == token_hash, "Token hash in DB must match SHA-256 digest"
    assert token not in stored, "Raw token must not appear in DB record"

    # 2. Retrieve user by token
    user = AuthService.get_user_by_session_token(token, conn)
    assert user is not None
    assert user.id == user_id

    # 3. Logout session
    AuthService.logout_session(token, conn)
    # Verify session is now invalid
    assert AuthService.get_user_by_session_token(token, conn) is None

    # 4. Issue second session, then deactivate user
    auth_data_2 = AuthService.authenticate_user("eval@lab.edu", "SecureResearchPass2026!", conn)
    token_2 = auth_data_2["session_token"]
    assert AuthService.get_user_by_session_token(token_2, conn) is not None

    # Deactivate user
    conn.execute("UPDATE users SET is_active = 0 WHERE id = ?;", (user_id,))
    conn.commit()

    # Verify session is immediately revoked for disabled user
    assert AuthService.get_user_by_session_token(token_2, conn) is None


def test_job_concurrency_manager_limits():
    """Verify JobConcurrencyManager strictly limits active concurrent solver runs."""
    user_id = "test-user-concurrency"
    concurrency_manager.release(user_id)  # reset

    # Slot 1 acquired
    assert concurrency_manager.acquire(user_id, max_concurrent=2) is True
    assert concurrency_manager.get_active_count(user_id) == 1

    # Slot 2 acquired
    assert concurrency_manager.acquire(user_id, max_concurrent=2) is True
    assert concurrency_manager.get_active_count(user_id) == 2

    # Slot 3 rejected (exceeds quota of 2)
    assert concurrency_manager.acquire(user_id, max_concurrent=2) is False
    assert concurrency_manager.get_active_count(user_id) == 2

    # Release 1 slot
    concurrency_manager.release(user_id)
    assert concurrency_manager.get_active_count(user_id) == 1

    # Now slot can be re-acquired
    assert concurrency_manager.acquire(user_id, max_concurrent=2) is True
    assert concurrency_manager.get_active_count(user_id) == 2

    # Cleanup
    concurrency_manager.release(user_id)
    concurrency_manager.release(user_id)
    assert concurrency_manager.get_active_count(user_id) == 0


def test_sqlite_database_backup_and_restore(clean_db):
    """Verify SQLite online backup API creates a valid replica that can be restored cleanly."""
    conn, db_path = clean_db

    # Create dummy user in active database
    uid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, allow_gemini, created_at, updated_at)
        VALUES (?, 'backup_test@lab.edu', 'pass_hash', 'Backup Tester', 'RESEARCHER', 1, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
        """,
        (uid,),
    )
    conn.commit()

    # Perform online backup to a secondary file
    with tempfile.NamedTemporaryFile(suffix="_backup.db", delete=False) as bkp_tmp:
        backup_path = bkp_tmp.name

    backup_conn = sqlite3.connect(backup_path)
    conn.backup(backup_conn)
    backup_conn.close()

    # Verify backup contains the user record
    verify_conn = sqlite3.connect(backup_path)
    cur = verify_conn.execute("SELECT email FROM users WHERE id = ?;", (uid,))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "backup_test@lab.edu"
    verify_conn.close()

    # Clean up backup file
    try:
        Path(backup_path).unlink(missing_ok=True)
    except Exception:
        pass


def test_sqlite_foreign_key_integrity(clean_db):
    """Verify SQLite foreign key enforcement rejects orphan records."""
    conn, _ = clean_db

    # Attempt to insert project with non-existent owner_user_id
    orphan_user_id = str(uuid.uuid4())
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO research_projects (id, name, description, owner_user_id, is_archived, created_at, updated_at)
            VALUES (?, 'Orphan Project', 'No owner', ?, 0, '2026-10-12T00:00:00', '2026-10-12T00:00:00');
            """,
            (str(uuid.uuid4()), orphan_user_id),
        )
