"""Project management, user data isolation, and experiment persistence service."""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.auth import User, UserRole
from app.models.projects import (
    OptimizationRunRecord,
    PermissionLevel,
    ProblemRecord,
    ProjectResponse,
    RunStatus,
    SaveExperimentRequest,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectService:
    """Provides user data isolation, project access control, and experiment persistence."""

    @staticmethod
    def create_project(
        name: str,
        description: Optional[str] = None,
        owner_user: User = None,
        conn: sqlite3.Connection = None,
    ) -> ProjectResponse:
        """Create a new research project bounded to the authenticated user."""
        proj_id = str(uuid.uuid4())
        now_str = _now_iso()

        conn.execute(
            """
            INSERT INTO research_projects (id, name, description, owner_user_id, is_archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?);
            """,
            (proj_id, name.strip(), description, owner_user.id, now_str, now_str),
        )
        conn.commit()

        return ProjectResponse(
            id=proj_id,
            name=name.strip(),
            description=description,
            owner_user_id=owner_user.id,
            is_archived=False,
            created_at=now_str,
            updated_at=now_str,
            problem_count=0,
            run_count=0,
        )

    @staticmethod
    def verify_project_access(
        project_id: str,
        user: User,
        min_permission: PermissionLevel,
        conn: sqlite3.Connection,
    ) -> sqlite3.Row:
        """Verify user authorization for a specific project. Enforces strict IDOR protection."""
        cursor = conn.execute("SELECT * FROM research_projects WHERE id = ?;", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise KeyError(f"Project '{project_id}' was not found.")

        # Admin has root access to all projects
        if user.role == UserRole.ADMIN:
            return project

        # Project owner has full permissions
        if project["owner_user_id"] == user.id:
            return project

        # Check explicit access grant
        cursor = conn.execute(
            "SELECT permission FROM access_grants WHERE project_id = ? AND user_id = ?;",
            (project_id, user.id),
        )
        grant = cursor.fetchone()
        if not grant:
            raise PermissionError(f"Access denied: You do not have permission to access project '{project_id}'.")

        granted_perm = grant["permission"]
        perm_hierarchy = {"VIEW": 1, "EDIT": 2, "ADMIN": 3}
        required_level = perm_hierarchy.get(min_permission.value, 1)
        actual_level = perm_hierarchy.get(granted_perm, 1)

        if actual_level < required_level:
            raise PermissionError(
                f"Insufficient permissions: required '{min_permission.value}', but you have '{granted_perm}'."
            )

        return project

    @staticmethod
    def list_user_projects(user: User, conn: sqlite3.Connection) -> List[ProjectResponse]:
        """List all research projects accessible to the user with run/problem counts."""
        if user.role == UserRole.ADMIN:
            cursor = conn.execute(
                """
                SELECT p.*,
                       (SELECT COUNT(*) FROM facility_problems WHERE project_id = p.id) as problem_count,
                       (SELECT COUNT(*) FROM optimization_runs WHERE project_id = p.id) as run_count
                FROM research_projects p
                WHERE p.is_archived = 0
                ORDER BY p.updated_at DESC;
                """
            )
        else:
            cursor = conn.execute(
                """
                SELECT p.*,
                       (SELECT COUNT(*) FROM facility_problems WHERE project_id = p.id) as problem_count,
                       (SELECT COUNT(*) FROM optimization_runs WHERE project_id = p.id) as run_count
                FROM research_projects p
                LEFT JOIN access_grants g ON p.id = g.project_id AND g.user_id = ?
                WHERE p.is_archived = 0 AND (p.owner_user_id = ? OR g.id IS NOT NULL)
                ORDER BY p.updated_at DESC;
                """,
                (user.id, user.id),
            )

        return [
            ProjectResponse(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                owner_user_id=r["owner_user_id"],
                is_archived=bool(r["is_archived"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                problem_count=r["problem_count"],
                run_count=r["run_count"],
            )
            for r in cursor.fetchall()
        ]

    @staticmethod
    def save_problem(
        project_id: str,
        name: str,
        facility_data: Dict[str, Any],
        user: User,
        conn: sqlite3.Connection,
    ) -> ProblemRecord:
        """Persist a factory problem within a project (requires EDIT permission)."""
        ProjectService.verify_project_access(project_id, user, PermissionLevel.EDIT, conn)

        prob_id = facility_data.get("id") or str(uuid.uuid4())
        data_json = json.dumps(facility_data, sort_keys=True)
        prob_hash = hashlib.sha256(data_json.encode("utf-8")).hexdigest()
        now_str = _now_iso()

        conn.execute(
            """
            INSERT OR REPLACE INTO facility_problems (id, project_id, name, problem_hash, facility_data, owner_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (prob_id, project_id, name.strip(), prob_hash, data_json, user.id, now_str, now_str),
        )
        conn.commit()

        return ProblemRecord(
            id=prob_id,
            project_id=project_id,
            name=name.strip(),
            problem_hash=prob_hash,
            facility_data=facility_data,
            owner_user_id=user.id,
            created_at=now_str,
            updated_at=now_str,
        )

    @staticmethod
    def list_project_problems(
        project_id: str,
        user: User,
        conn: sqlite3.Connection,
    ) -> List[ProblemRecord]:
        """List all facility problems associated with a project."""
        ProjectService.verify_project_access(project_id, user, PermissionLevel.VIEW, conn)

        cursor = conn.execute(
            """
            SELECT id, project_id, name, problem_hash, facility_data, owner_user_id, created_at, updated_at
            FROM facility_problems
            WHERE project_id = ?
            ORDER BY created_at DESC;
            """,
            (project_id,),
        )
        return [
            ProblemRecord(
                id=r["id"],
                project_id=r["project_id"],
                name=r["name"],
                problem_hash=r["problem_hash"],
                facility_data=json.loads(r["facility_data"]),
                owner_user_id=r["owner_user_id"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in cursor.fetchall()
        ]

    @staticmethod
    def save_experiment_run(
        req: SaveExperimentRequest,
        user: User,
        conn: sqlite3.Connection,
    ) -> OptimizationRunRecord:
        """Persist an immutable reproducible experiment run and its layout."""
        ProjectService.verify_project_access(req.project_id, user, PermissionLevel.EDIT, conn)

        run_id = str(uuid.uuid4())
        now_str = _now_iso()
        params_json = json.dumps(req.parameters, sort_keys=True)
        metrics_json = json.dumps(req.canonical_metrics, sort_keys=True)

        conn.execute(
            """
            INSERT INTO optimization_runs (
                id, project_id, problem_id, user_id, algorithm_name, algorithm_version,
                flodss_version, parameters, random_seed, status, termination_reason,
                runtime_ms, problem_hash, evaluation_config_hash, layout_signature,
                is_feasible, canonical_metrics, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'v1.0.0-rc.1', ?, ?, 'COMPLETED', ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                run_id,
                req.project_id,
                req.problem_id,
                user.id,
                req.algorithm_name,
                req.algorithm_version or "1.0.0",
                params_json,
                req.random_seed,
                req.termination_reason,
                req.runtime_ms,
                req.problem_hash,
                req.evaluation_config_hash,
                req.layout_signature,
                int(req.is_feasible),
                metrics_json,
                now_str,
                now_str,
            ),
        )

        # Store candidate layout if provided
        if req.layout_data:
            layout_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO candidate_layouts (id, run_id, layout_signature, layout_data, is_pareto_optimal, created_at)
                VALUES (?, ?, ?, ?, 1, ?);
                """,
                (layout_id, run_id, req.layout_signature, json.dumps(req.layout_data), now_str),
            )

        # Store evaluation report if provided
        if req.evaluation_report:
            eval_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO evaluation_results (id, run_id, layout_signature, report_data, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (eval_id, run_id, req.layout_signature, json.dumps(req.evaluation_report), now_str),
            )

        conn.commit()

        return OptimizationRunRecord(
            id=run_id,
            project_id=req.project_id,
            problem_id=req.problem_id,
            user_id=user.id,
            algorithm_name=req.algorithm_name,
            algorithm_version=req.algorithm_version or "1.0.0",
            flodss_version="v1.0.0-rc.1",
            parameters=req.parameters,
            random_seed=req.random_seed,
            status=RunStatus.COMPLETED,
            termination_reason=req.termination_reason,
            runtime_ms=req.runtime_ms,
            problem_hash=req.problem_hash,
            evaluation_config_hash=req.evaluation_config_hash,
            layout_signature=req.layout_signature,
            is_feasible=req.is_feasible,
            canonical_metrics=req.canonical_metrics,
            created_at=now_str,
            completed_at=now_str,
        )

    @staticmethod
    def list_project_runs(
        project_id: str,
        user: User,
        conn: sqlite3.Connection,
    ) -> List[OptimizationRunRecord]:
        """List all optimization experiment runs within a project."""
        ProjectService.verify_project_access(project_id, user, PermissionLevel.VIEW, conn)

        cursor = conn.execute(
            """
            SELECT * FROM optimization_runs
            WHERE project_id = ?
            ORDER BY created_at DESC;
            """,
            (project_id,),
        )
        return [
            OptimizationRunRecord(
                id=r["id"],
                project_id=r["project_id"],
                problem_id=r["problem_id"],
                user_id=r["user_id"],
                algorithm_name=r["algorithm_name"],
                algorithm_version=r["algorithm_version"],
                flodss_version=r["flodss_version"],
                parameters=json.loads(r["parameters"]),
                random_seed=r["random_seed"],
                status=RunStatus(r["status"]),
                termination_reason=r["termination_reason"],
                runtime_ms=r["runtime_ms"],
                problem_hash=r["problem_hash"],
                evaluation_config_hash=r["evaluation_config_hash"],
                layout_signature=r["layout_signature"],
                is_feasible=bool(r["is_feasible"]),
                canonical_metrics=json.loads(r["canonical_metrics"]) if r["canonical_metrics"] else None,
                created_at=r["created_at"],
                completed_at=r["completed_at"],
            )
            for r in cursor.fetchall()
        ]

    @staticmethod
    def get_experiment_run(
        run_id: str,
        user: User,
        conn: sqlite3.Connection,
    ) -> Dict[str, Any]:
        """Retrieve full experiment details and attached layout with IDOR verification."""
        cursor = conn.execute("SELECT * FROM optimization_runs WHERE id = ?;", (run_id,))
        run = cursor.fetchone()
        if not run:
            raise KeyError(f"Experiment run '{run_id}' not found.")

        # Verify access through parent project
        ProjectService.verify_project_access(run["project_id"], user, PermissionLevel.VIEW, conn)

        # Fetch attached layout
        cursor = conn.execute("SELECT layout_data FROM candidate_layouts WHERE run_id = ? LIMIT 1;", (run_id,))
        layout_row = cursor.fetchone()
        layout_data = json.loads(layout_row["layout_data"]) if layout_row else None

        # Fetch attached evaluation
        cursor = conn.execute("SELECT report_data FROM evaluation_results WHERE run_id = ? LIMIT 1;", (run_id,))
        eval_row = cursor.fetchone()
        eval_data = json.loads(eval_row["report_data"]) if eval_row else None

        return {
            "run": OptimizationRunRecord(
                id=run["id"],
                project_id=run["project_id"],
                problem_id=run["problem_id"],
                user_id=run["user_id"],
                algorithm_name=run["algorithm_name"],
                algorithm_version=run["algorithm_version"],
                flodss_version=run["flodss_version"],
                parameters=json.loads(run["parameters"]),
                random_seed=run["random_seed"],
                status=RunStatus(run["status"]),
                termination_reason=run["termination_reason"],
                runtime_ms=run["runtime_ms"],
                problem_hash=run["problem_hash"],
                evaluation_config_hash=run["evaluation_config_hash"],
                layout_signature=run["layout_signature"],
                is_feasible=bool(run["is_feasible"]),
                canonical_metrics=json.loads(run["canonical_metrics"]) if run["canonical_metrics"] else None,
                created_at=run["created_at"],
                completed_at=run["completed_at"],
            ),
            "layout": layout_data,
            "evaluation": eval_data,
        }
