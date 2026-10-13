"""Phase 14 End-to-End Acceptance Tests: V1.0 Product Experience & Release Candidate."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.models.problem import FacilityLayoutProblem, Facility, Department, Flow, Relationship
from app.services.problem_service import problem_service
from app.services.layout_normalizer import generate_layout_signature
from app.models.representation import ContinuousLayout, ContinuousPlacement


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestPhase14ReleaseCandidateMetadata:
    """Test platform versioning and release candidate metadata."""

    def test_version_is_release_candidate_1(self, client):
        """Verify FLODSS version is explicitly set to 1.0.0-rc.1."""
        assert settings.VERSION == "1.0.0-rc.1"

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0-rc.1"
        assert data["status"] == "healthy"
        assert "registered_algorithms" in data
        assert data["registered_algorithms"] >= 4

    def test_offline_ai_confidentiality_default(self, client):
        """Verify Gemini AI integration is disabled by default for data confidentiality."""
        assert settings.AI_ENABLED is False

        response = client.get("/api/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ai_enabled"] is False
        assert data["default_mode"] == "local"
        assert data["has_api_key"] is False
        assert "strictly whitelisted" in data["confidentiality_guarantee"]


class TestPhase14ProblemModelingAndValidation:
    """Test custom problem authoring, matrices, and constraint validation."""

    def test_custom_problem_validation_success(self, client):
        """Test creating and validating a custom factory problem payload."""
        payload = {
            "id": "FLP_CUSTOM_TEST_01",
            "name": "Custom Pilot Assembly Facility",
            "facility": {
                "id": "FAC_01",
                "name": "Main Hall",
                "width": 100.0,
                "height": 60.0,
                "area": 6000.0,
                "reserved_zones": [
                    {
                        "id": "RZ_CORRIDOR",
                        "type": "aisle_corridor",
                        "bounding_box": {"x_min": 45.0, "y_min": 0.0, "x_max": 55.0, "y_max": 60.0},
                        "strict": True,
                    }
                ],
            },
            "departments": [
                {
                    "id": "D1",
                    "name": "Receiving",
                    "required_area": 1200.0,
                    "min_aspect_ratio": 1.0,
                    "max_aspect_ratio": 3.0,
                    "fixed_position": {"x": 0.0, "y": 0.0},
                },
                {
                    "id": "D2",
                    "name": "Machining",
                    "required_area": 1500.0,
                    "min_aspect_ratio": 1.0,
                    "max_aspect_ratio": 3.0,
                },
                {
                    "id": "D3",
                    "name": "Assembly",
                    "required_area": 1800.0,
                    "min_aspect_ratio": 1.0,
                    "max_aspect_ratio": 3.0,
                },
                {
                    "id": "D4",
                    "name": "Shipping",
                    "required_area": 1000.0,
                    "min_aspect_ratio": 1.0,
                    "max_aspect_ratio": 3.0,
                },
            ],
            "flows": [
                {"source_department": "D1", "target_department": "D2", "quantity": 150.0, "cost_per_unit_distance": 1.0},
                {"source_department": "D2", "target_department": "D3", "quantity": 120.0, "cost_per_unit_distance": 1.0},
                {"source_department": "D3", "target_department": "D4", "quantity": 100.0, "cost_per_unit_distance": 1.0},
            ],
            "relationships": [
                {"department_a": "D1", "department_b": "D2", "relationship_type": "A", "score": 16.0},
                {"department_a": "D2", "department_b": "D3", "relationship_type": "E", "score": 8.0},
                {"department_a": "D3", "department_b": "D4", "relationship_type": "I", "score": 4.0},
            ],
        }

        response = client.post("/api/problems/validate", json=payload)
        assert response.status_code == 200
        report = response.json()
        assert report["is_valid"] is True
        assert len(report["errors"]) == 0
        assert report["fingerprint"] is not None
        assert report["fingerprint"]["department_count"] == 4

    def test_custom_problem_validation_over_utilization(self, client):
        """Test that problem validation detects when total department area exceeds facility boundary."""
        payload = {
            "id": "FLP_OVERSIZED",
            "name": "Oversized Facility",
            "facility": {"id": "FAC_01", "name": "Hall", "width": 50.0, "height": 50.0, "area": 2500.0},
            "departments": [
                {"id": "D1", "name": "Warehouse", "required_area": 2000.0},
                {"id": "D2", "name": "Production", "required_area": 1500.0},
            ],
            "flows": [],
            "relationships": [],
        }

        response = client.post("/api/problems/validate", json=payload)
        assert response.status_code == 200
        report = response.json()
        assert report["is_valid"] is False
        assert any("area" in err.lower() or "exceeds" in err.lower() for err in report["errors"])


class TestPhase14AlgorithmExecutionWithCustomProblem:
    """Test solver execution using inline custom problems."""

    def test_aldep_solve_with_inline_problem(self, client):
        """Test ALDEP solver accepting inline custom problem definition."""
        payload = {
            "problem": {
                "id": "FLP_INLINE_ALDEP",
                "name": "Inline ALDEP Test",
                "facility": {"id": "F1", "name": "Main", "width": 60.0, "height": 40.0, "area": 2400.0},
                "departments": [
                    {"id": "D1", "name": "A", "required_area": 600.0},
                    {"id": "D2", "name": "B", "required_area": 600.0},
                    {"id": "D3", "name": "C", "required_area": 600.0},
                    {"id": "D4", "name": "D", "required_area": 600.0},
                ],
                "flows": [
                    {"source_department": "D1", "target_department": "D2", "quantity": 50.0},
                    {"source_department": "D2", "target_department": "D3", "quantity": 40.0},
                ],
                "relationships": [
                    {"department_a": "D1", "department_b": "D2", "relationship_type": "A"},
                    {"department_a": "D2", "department_b": "D3", "relationship_type": "E"},
                ],
            },
            "config": {
                "random_seed": 42,
                "number_of_candidates": 3,
            },
        }

        response = client.post("/api/algorithms/aldep/solve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "continuous_layout" in data
        assert "solution" in data
        assert "evaluation" in data
        assert len(data["continuous_layout"]["placements"]) == 4

    def test_layout_signature_reproducibility(self):
        """Test deterministic layout signature generation across runs."""
        layout1 = ContinuousLayout(
            representation_type="continuous",
            facility_width=100.0,
            facility_height=60.0,
            placements={
                "D1": ContinuousPlacement(department_id="D1", x=0.0, y=0.0, width=20.0, height=30.0),
                "D2": ContinuousPlacement(department_id="D2", x=20.0, y=0.0, width=30.0, height=20.0),
            },
        )
        layout2 = ContinuousLayout(
            representation_type="continuous",
            facility_width=100.0,
            facility_height=60.0,
            placements={
                "D2": ContinuousPlacement(department_id="D2", x=20.0, y=0.0, width=30.0, height=20.0),
                "D1": ContinuousPlacement(department_id="D1", x=0.0, y=0.0, width=20.0, height=30.0),
            },
        )

        sig1 = generate_layout_signature(layout1)
        sig2 = generate_layout_signature(layout2)

        assert sig1 == sig2
        assert len(sig1) == 64  # Valid SHA-256 hex digest
