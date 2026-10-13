"""Project and experiment persistence routes with strict tenant isolation and IDOR protection."""

import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.auth import User, UserRole
from app.models.projects import (
    OptimizationRunRecord,
    PermissionLevel,
    ProblemRecord,
    ProjectCreate,
    ProjectResponse,
    SaveExperimentRequest,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Research Projects & Isolation"])


@router.get("", response_model=List[ProjectResponse], summary="List User Projects")
def list_projects(
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List all research projects accessible to the authenticated researcher or admin."""
    return ProjectService.list_user_projects(current_user, conn)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Create Project")
def create_project(
    req: ProjectCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER)),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a new research project bounded to the current user."""
    return ProjectService.create_project(
        name=req.name,
        description=req.description,
        owner_user=current_user,
        conn=conn,
    )


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get Project Details")
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get metadata for a single project with IDOR access check."""
    try:
        proj_row = ProjectService.verify_project_access(project_id, current_user, PermissionLevel.VIEW, conn)
        # Fetch problem and run counts
        cur = conn.execute("SELECT COUNT(*) FROM facility_problems WHERE project_id = ?;", (project_id,))
        prob_count = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM optimization_runs WHERE project_id = ?;", (project_id,))
        run_count = cur.fetchone()[0]

        return ProjectResponse(
            id=proj_row["id"],
            name=proj_row["name"],
            description=proj_row["description"],
            owner_user_id=proj_row["owner_user_id"],
            is_archived=bool(proj_row["is_archived"]),
            created_at=proj_row["created_at"],
            updated_at=proj_row["updated_at"],
            problem_count=prob_count,
            run_count=run_count,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{project_id}/problems", response_model=ProblemRecord, status_code=status.HTTP_201_CREATED, summary="Save Problem to Project")
def save_problem_to_project(
    project_id: str,
    payload: Dict[str, Any],
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER)),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Save or associate a facility problem definition with a project."""
    name = payload.get("name") or payload.get("id") or "Untitled Problem"
    facility_data = payload.get("facility_data") or payload
    try:
        return ProjectService.save_problem(
            project_id=project_id,
            name=name,
            facility_data=facility_data,
            user=current_user,
            conn=conn,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{project_id}/problems", response_model=List[ProblemRecord], summary="List Project Problems")
def list_project_problems(
    project_id: str,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List all facility problem instances stored inside a project."""
    try:
        return ProjectService.list_project_problems(project_id, current_user, conn)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{project_id}/experiments", response_model=OptimizationRunRecord, status_code=status.HTTP_201_CREATED, summary="Save Experiment Run")
def save_experiment_run(
    project_id: str,
    req: SaveExperimentRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER)),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Save an immutable optimization run record with its Pareto/canonical layout."""
    if req.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project ID mismatch between route and payload.")
    try:
        return ProjectService.save_experiment_run(req, current_user, conn)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{project_id}/experiments", response_model=List[OptimizationRunRecord], summary="List Project Experiment Runs")
def list_project_experiments(
    project_id: str,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List all past experiment runs for a project."""
    try:
        return ProjectService.list_project_runs(project_id, current_user, conn)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Standalone experiment detail route mounted under /experiments
experiment_router = APIRouter(prefix="/experiments", tags=["Research Experiments"])


@experiment_router.get("/{run_id}", summary="Get Experiment Run Details")
def get_experiment_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Fetch run record, candidate layout data, and evaluation results with IDOR enforcement."""
    try:
        return ProjectService.get_experiment_run(run_id, current_user, conn)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
