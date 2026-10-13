"""Pytest fixtures for Facility Layout System tests."""

import pytest
from app.models.facility import Facility
from app.models.department import Department
from app.models.flow import Flow
from app.models.relationship import Relationship, ClosenessRating
from app.models.constraint import Constraint, ConstraintType, ConstraintClassification
from app.models.problem import FacilityLayoutProblem, ObjectiveConfig, PrimaryObjective
from app.models.geometry import Point2D, Dimensions2D
from app.models.solution import LayoutSolution, DepartmentPlacement
from app.main import app
from app.api.deps import get_current_user
from app.db.database import db_manager
from app.models.auth import User, UserRole
from app.services.auth_service import AuthService


from pathlib import Path
from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Ensure database schema and migrations are initialized for test execution."""
    secret_paths = [
        Path(settings.DATABASE_PATH).parent / ".admin_credentials.secret",
        Path(__file__).resolve().parent.parent / "data" / ".admin_credentials.secret",
    ]
    for sp in secret_paths:
        if sp.exists():
            with open(sp, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("FLODSS_ADMIN_PASSWORD="):
                        settings.DEFAULT_ADMIN_PASSWORD = line.split("=", 1)[1].strip()
            break

    db_manager.run_migrations()
    with db_manager.get_connection() as conn:
        AuthService.ensure_admin_user(conn)


from app.core.security import concurrency_manager, rate_limiter


@pytest.fixture(autouse=True)
def override_auth_for_tests():
    """Default authenticated researcher fixture to maintain compatibility with all 377 unit tests."""
    concurrency_manager.reset_all()
    rate_limiter.reset_all()
    test_user = User(
        id="usr_test_default",
        email="test_researcher@flodss.local",
        full_name="Default Test Researcher",
        role=UserRole.ADMIN,
        is_active=True,
        allow_gemini=True,
        created_at="2026-10-12T00:00:00Z",
        updated_at="2026-10-12T00:00:00Z",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    concurrency_manager.reset_all()
    rate_limiter.reset_all()
    app.dependency_overrides[get_current_user] = lambda: test_user


@pytest.fixture
def sample_facility() -> Facility:
    """Fixture providing a standard 100x60m plant facility."""
    return Facility(
        id="FAC_01",
        name="Main Assembly Plant",
        width=100.0,
        height=60.0,
        metadata={"floor": "Level 1"},
    )


@pytest.fixture
def sample_departments() -> list[Department]:
    """Fixture providing standard production departments."""
    return [
        Department(
            id="DEP_RECEIVING",
            name="Receiving & Raw Storage",
            required_area=600.0,
            min_width=20.0,
            max_width=40.0,
        ),
        Department(
            id="DEP_MACHINING",
            name="CNC Machining Center",
            required_area=1200.0,
            min_width=25.0,
            max_width=50.0,
        ),
        Department(
            id="DEP_ASSEMBLY",
            name="Main Assembly Line",
            required_area=1500.0,
            min_width=30.0,
            max_width=60.0,
        ),
        Department(
            id="DEP_SHIPPING",
            name="Finished Goods & Shipping",
            required_area=800.0,
            min_width=20.0,
            max_width=40.0,
        ),
    ]


@pytest.fixture
def sample_flows() -> list[Flow]:
    """Fixture providing standard material flows."""
    return [
        Flow(source_department="DEP_RECEIVING", target_department="DEP_MACHINING", quantity=150.0),
        Flow(source_department="DEP_MACHINING", target_department="DEP_ASSEMBLY", quantity=140.0),
        Flow(source_department="DEP_ASSEMBLY", target_department="DEP_SHIPPING", quantity=135.0),
    ]


@pytest.fixture
def sample_relationships() -> list[Relationship]:
    """Fixture providing SLP closeness ratings."""
    return [
        Relationship(
            department_a="DEP_RECEIVING",
            department_b="DEP_MACHINING",
            relationship_type=ClosenessRating.A,
            reason="High material volume",
        ),
        Relationship(
            department_a="DEP_MACHINING",
            department_b="DEP_ASSEMBLY",
            relationship_type=ClosenessRating.E,
            reason="Continuous parts transfer",
        ),
        Relationship(
            department_a="DEP_RECEIVING",
            department_b="DEP_SHIPPING",
            relationship_type=ClosenessRating.X,
            reason="Traffic interference / Dock safety separation",
        ),
    ]


@pytest.fixture
def sample_constraints() -> list[Constraint]:
    """Fixture providing sample hard and soft constraints."""
    return [
        Constraint(
            id="CST_NON_OVERLAP",
            type=ConstraintType.NON_OVERLAPPING,
            classification=ConstraintClassification.HARD,
        ),
        Constraint(
            id="CST_SHIPPING_DOCK",
            type=ConstraintType.BOUNDARY,
            involved_departments=["DEP_SHIPPING"],
            classification=ConstraintClassification.HARD,
        ),
    ]


@pytest.fixture
def sample_problem(
    sample_facility: Facility,
    sample_departments: list[Department],
    sample_flows: list[Flow],
    sample_relationships: list[Relationship],
    sample_constraints: list[Constraint],
) -> FacilityLayoutProblem:
    """Fixture providing a complete validated FacilityLayoutProblem instance."""
    return FacilityLayoutProblem(
        id="CASE_TEST_01",
        name="Benchmark Case 01",
        facility=sample_facility,
        departments=sample_departments,
        flows=sample_flows,
        relationships=sample_relationships,
        constraints=sample_constraints,
        objective_config=ObjectiveConfig(
            primary_objective=PrimaryObjective.MINIMIZE_FLOW_DISTANCE
        ),
    )


@pytest.fixture
def sample_solution(sample_problem: FacilityLayoutProblem) -> LayoutSolution:
    """Fixture providing a sample feasible LayoutSolution."""
    placements = {
        "DEP_RECEIVING": DepartmentPlacement(
            department_id="DEP_RECEIVING",
            origin=Point2D(x=0.0, y=0.0),
            dimensions=Dimensions2D(width=20.0, height=30.0),
        ),
        "DEP_MACHINING": DepartmentPlacement(
            department_id="DEP_MACHINING",
            origin=Point2D(x=25.0, y=0.0),
            dimensions=Dimensions2D(width=30.0, height=40.0),
        ),
        "DEP_ASSEMBLY": DepartmentPlacement(
            department_id="DEP_ASSEMBLY",
            origin=Point2D(x=60.0, y=0.0),
            dimensions=Dimensions2D(width=30.0, height=50.0),
        ),
        "DEP_SHIPPING": DepartmentPlacement(
            department_id="DEP_SHIPPING",
            origin=Point2D(x=20.0, y=40.0),
            dimensions=Dimensions2D(width=40.0, height=20.0),
        ),
    }

    positions = {d_id: p.centroid for d_id, p in placements.items()}
    dimensions = {d_id: p.dimensions for d_id, p in placements.items()}

    return LayoutSolution(
        problem_id=sample_problem.id,
        algorithm_name="mock_baseline_solver",
        algorithm_version="0.1.0",
        placements=placements,
        department_positions=positions,
        department_dimensions=dimensions,
        objective_values={"total_flow_distance": 2150.0},
        feasibility_status=True,
    )
