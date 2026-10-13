"""Unit tests for Phase 2: Facility Layout Problem Modeling & Data Ingestion."""

import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.problem import FacilityLayoutProblem
from app.services.matrix_parser import (
    parse_from_to_matrix,
    flows_to_matrix,
    parse_relationship_matrix,
)
from app.services.problem_loader import load_problem, JSONProblemLoader
from app.services.problem_analyzer import ProblemAnalyzer
from app.services.problem_service import problem_service

client = TestClient(app)
SAMPLE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "sample_plant.json"


@pytest.fixture
def minimal_valid_dict() -> dict:
    """Fixture returning a minimal valid problem dictionary."""
    return {
        "id": "MINIMAL_01",
        "name": "Minimal Plant",
        "facility": {
            "id": "F1",
            "name": "Facility 1",
            "width": 100.0,
            "height": 50.0,
            "area": 5000.0,
        },
        "departments": [
            {"id": "D1", "name": "Dept 1", "required_area": 1000.0},
            {"id": "D2", "name": "Dept 2", "required_area": 1500.0},
            {"id": "D3", "name": "Dept 3", "required_area": 800.0},
        ],
        "flows": [
            {"source_department": "D1", "target_department": "D2", "quantity": 100.0},
            {"source_department": "D2", "target_department": "D3", "quantity": 80.0},
        ],
        "relationships": [
            {"department_a": "D1", "department_b": "D2", "relationship_type": "A"},
            {"department_a": "D2", "department_b": "D3", "relationship_type": "E"},
        ],
        "constraints": [
            {
                "id": "C1",
                "type": "minimum_distance",
                "involved_departments": ["D1", "D3"],
                "parameters": {"distance": 15.0},
                "classification": "HARD",
            }
        ],
        "objectives": {
            "material_handling_cost": {"enabled": True, "weight": 1.0, "direction": "minimize"},
            "relationship_score": {"enabled": True, "weight": 0.5, "direction": "maximize"},
        },
    }


class TestProblemIngestionAndValidation:
    """Tests for problem loading, schema validation, and integrity constraints."""

    # 1. Valid JSON problem loads successfully
    def test_valid_json_problem_loads_successfully(self, minimal_valid_dict):
        problem = load_problem(minimal_valid_dict)
        assert isinstance(problem, FacilityLayoutProblem)
        assert problem.id == "MINIMAL_01"
        assert len(problem.departments) == 3
        assert len(problem.flows) == 2
        assert "material_handling_cost" in problem.objective_config.objectives

    # 2. Invalid JSON is rejected
    def test_invalid_json_is_rejected(self):
        report = problem_service.validate_problem({"invalid_key": "junk"})
        assert report.is_valid is False
        assert len(report.errors) > 0

    # 3. Unknown department in flow rejected
    def test_unknown_department_in_flow_rejected(self, minimal_valid_dict):
        bad_dict = dict(minimal_valid_dict)
        bad_dict["flows"] = [
            {"source_department": "D1", "target_department": "UNKNOWN_DEP", "quantity": 50.0}
        ]
        report = problem_service.validate_problem(bad_dict)
        assert report.is_valid is False
        assert any("UNKNOWN_DEP" in err for err in report.errors)

    # 4. Unknown department in relationship rejected
    def test_unknown_department_in_relationship_rejected(self, minimal_valid_dict):
        bad_dict = dict(minimal_valid_dict)
        bad_dict["relationships"] = [
            {"department_a": "GHOST_DEPT", "department_b": "D2", "relationship_type": "A"}
        ]
        report = problem_service.validate_problem(bad_dict)
        assert report.is_valid is False
        assert any("GHOST_DEPT" in err for err in report.errors)

    # 5. Unknown department in constraint rejected
    def test_unknown_department_in_constraint_rejected(self, minimal_valid_dict):
        bad_dict = dict(minimal_valid_dict)
        bad_dict["constraints"] = [
            {
                "id": "C_BAD",
                "type": "min_distance",
                "involved_departments": ["D1", "NON_EXISTENT_DEP"],
                "parameters": {"distance": 10.0},
            }
        ]
        report = problem_service.validate_problem(bad_dict)
        assert report.is_valid is False
        assert any("NON_EXISTENT_DEP" in err for err in report.errors)

    # 6. Negative flow rejected
    def test_negative_flow_rejected(self, minimal_valid_dict):
        bad_dict = dict(minimal_valid_dict)
        bad_dict["flows"] = [
            {"source_department": "D1", "target_department": "D2", "quantity": -50.0}
        ]
        report = problem_service.validate_problem(bad_dict)
        assert report.is_valid is False
        assert any("quantity" in err.lower() or "negative" in err.lower() for err in report.errors)

    # 7. Invalid objective rejected
    def test_invalid_objective_rejected(self, minimal_valid_dict):
        bad_dict = dict(minimal_valid_dict)
        bad_dict["objectives"] = {
            "flow_distance": {"enabled": True, "weight": -2.0, "direction": "minimize"}
        }
        report = problem_service.validate_problem(bad_dict)
        assert report.is_valid is False

        # Invalid direction rejected
        bad_dict2 = dict(minimal_valid_dict)
        bad_dict2["objectives"] = {
            "flow_distance": {"enabled": True, "weight": 1.0, "direction": "invalid_direction"}
        }
        report2 = problem_service.validate_problem(bad_dict2)
        assert report2.is_valid is False

    # 8. From-To matrix converts correctly
    def test_from_to_matrix_conversion(self):
        # 1. From 2D NumPy array
        dept_ids = ["A", "B", "C"]
        mat = np.array([
            [0, 100, 20],
            [0, 0, 50],
            [0, 0, 0],
        ])
        flows = parse_from_to_matrix(mat, department_ids=dept_ids)
        assert len(flows) == 3
        assert flows[0].source_department == "A"
        assert flows[0].target_department == "B"
        assert flows[0].quantity == 100.0
        assert flows[1].quantity == 20.0
        assert flows[2].quantity == 50.0

        # Invert back to matrix
        _, back_mat = flows_to_matrix(flows, dept_ids)
        np.testing.assert_array_equal(mat, back_mat)

        # 2. From CSV tabular string
        csv_text = """
        From/To, A, B, C
        A, 0, 100, 20
        B, 0, 0, 50
        C, 0, 0, 0
        """
        csv_flows = parse_from_to_matrix(csv_text)
        assert len(csv_flows) == 3
        assert csv_flows[0].quantity == 100.0

    # 9. Relationship matrix converts correctly
    def test_relationship_matrix_conversion(self):
        rel_csv = """
        department_a,department_b,relationship,reason
        DEP_A,DEP_B,A,High Material Flow
        DEP_B,DEP_C,E,Sequential Route
        DEP_A,DEP_C,X,Hazard Isolation
        """
        rels = parse_relationship_matrix(rel_csv)
        assert len(rels) == 3
        assert rels[0].relationship_type.value == "A"
        assert rels[0].score == 16.0
        assert rels[1].relationship_type.value == "E"
        assert rels[1].score == 8.0
        assert rels[2].relationship_type.value == "X"
        assert rels[2].score == -8.0

        # Invalid closeness rating rejected
        with pytest.raises(ValueError):
            parse_relationship_matrix([{"department_a": "A", "department_b": "B", "relationship": "Z"}])

    # 10. Sample factory problem loads successfully
    def test_sample_factory_problem_loads_successfully(self):
        assert SAMPLE_FILE.exists(), f"Sample plant file missing at {SAMPLE_FILE}"
        problem = load_problem(SAMPLE_FILE)
        assert problem.id == "FLP_INDUSTRIAL_10"
        assert len(problem.departments) == 10
        assert len(problem.flows) == 13
        assert len(problem.relationships) == 13
        assert len(problem.constraints) == 4
        assert problem.facility.area == 12000.0
        assert problem.total_required_area == 11000.0
        assert round(problem.area_utilization, 3) == 0.917

        # Test fingerprint extraction
        fp = ProblemAnalyzer.extract_fingerprint(problem)
        assert fp.department_count == 10
        assert fp.flow_count == 13
        assert fp.undesirable_relationships_count == 3
        assert fp.hard_constraints_count == 2
        assert fp.soft_constraints_count == 2


class TestProblemAPIEndpoints:
    """Tests for REST API problem endpoints."""

    # 11. API example listing works
    def test_api_list_example_problems(self):
        response = client.get("/api/problems/examples")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        industrial = next((p for p in data if p["id"] == "FLP_INDUSTRIAL_10"), None)
        assert industrial is not None
        assert "id" in industrial
        assert "facility_area" in industrial
        assert "department_count" in industrial
        assert industrial["department_count"] == 10

    def test_api_get_example_by_id(self):
        response = client.get("/api/problems/examples/FLP_INDUSTRIAL_10")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "FLP_INDUSTRIAL_10"
        assert len(data["departments"]) == 10

        # Not found test
        not_found = client.get("/api/problems/examples/NON_EXISTENT_ID")
        assert not_found.status_code == 404

    # 12. API problem validation works
    def test_api_problem_validation(self, minimal_valid_dict):
        # Valid payload
        response = client.post("/api/problems/validate", json=minimal_valid_dict)
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
        assert data["fingerprint"]["department_count"] == 3

        # Invalid payload
        invalid_payload = dict(minimal_valid_dict)
        invalid_payload["facility"]["width"] = -50.0  # Invalid width
        res_invalid = client.post("/api/problems/validate", json=invalid_payload)
        assert res_invalid.status_code == 200
        data_inv = res_invalid.json()
        assert data_inv["is_valid"] is False
        assert len(data_inv["errors"]) > 0
