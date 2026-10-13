"""Tests for Phase 13: Industrial Validation, Security Hardening & Zero-Tolerance Integrity."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.models import (
    GrantConsentRequest,
    PresetQuestionType,
    SanitizedAIExplanationPayload,
    StructuredAIExplanation,
)
from app.ai.sanitizer import PayloadSanitizer, ServerConsentStore
from app.ai.validator import ExplanationOutputValidator
from app.evaluation.canonical import CanonicalEvaluationService
from app.models.problem import FacilityLayoutProblem
from app.algorithms.ga.models import GAConfig
from app.algorithms.ga.solver import GeneticLayoutAlgorithm
from app.services.problem_service import ProblemService

DATA_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_consent_store():
    ServerConsentStore.reset()
    yield
    ServerConsentStore.reset()


class TestSyntheticIndustrialDatasets:
    """Validate 4 synthetic industrial datasets against engineering rules and problem schemas."""

    @pytest.mark.parametrize("filename,expected_id,expected_depts,expected_min_util", [
        ("synthetic_high_density_15.json", "HIGH_DENSITY_15", 15, 0.89),
        ("synthetic_high_density_20.json", "HIGH_DENSITY_20", 20, 0.95),
        ("synthetic_constrained_factory_12.json", "CONSTRAINED_FACTORY_12", 12, 0.80),
        ("synthetic_logistics_factory_15.json", "LOGISTICS_FACTORY_15", 15, 0.84),
    ])
    def test_synthetic_problem_validation(self, filename, expected_id, expected_depts, expected_min_util):
        svc = ProblemService()
        prob_path = DATA_EXAMPLES_DIR / filename
        assert prob_path.exists(), f"Benchmark file {filename} does not exist"

        problem = svc.load_problem(prob_path)
        assert isinstance(problem, FacilityLayoutProblem)
        assert problem.id == expected_id
        assert len(problem.departments) == expected_depts

        report = svc.validate_problem(problem)
        assert report.is_valid is True
        assert len(report.errors) == 0

        total_area = sum(d.required_area for d in problem.departments)
        fac_area = problem.facility.width * problem.facility.height
        util = total_area / fac_area
        assert util >= expected_min_util

    def test_constrained_factory_12_features(self):
        svc = ProblemService()
        problem = svc.load_problem(DATA_EXAMPLES_DIR / "synthetic_constrained_factory_12.json")
        
        # Verify fixed department
        fixed_depts = [d for d in problem.departments if d.fixed_position is not None]
        assert len(fixed_depts) == 1
        gate = fixed_depts[0]
        assert gate.id == "DEP_01_GATE"
        assert gate.fixed_position.x == 0.0
        assert gate.fixed_position.y == 0.0

        # Verify reserved zone (corridor)
        corridors = [z for z in problem.facility.reserved_zones if "CORRIDOR" in z.id.upper() or "SPINE" in z.id.upper()]
        assert len(corridors) == 1
        c = corridors[0]
        assert c.bounding_box.x_min == 75.0
        assert c.bounding_box.x_max == 85.0
        assert c.bounding_box.y_min == 0.0
        assert c.bounding_box.y_max == 100.0


class TestEngineeringConstraintsSolver:
    """Verify solver execution compliance on constrained industrial instances."""

    def test_genetic_algorithm_respects_fixed_position_on_constrained_12(self):
        svc = ProblemService()
        problem = svc.load_problem(DATA_EXAMPLES_DIR / "synthetic_constrained_factory_12.json")
        
        ga = GeneticLayoutAlgorithm()
        cfg = GAConfig(
            population_size=12,
            max_generations=6,
            random_seed=42,
            time_budget_seconds=5.0,
        )
        result = ga.solve_with_result(problem, config=cfg)
        assert result.best_layout is not None

        # Verify fixed department is placed exactly at fixed coordinates
        gate_placement = result.best_layout.placements.get("DEP_01_GATE")
        assert gate_placement is not None
        assert gate_placement.x == 0.0
        assert gate_placement.y == 0.0

        # Evaluate canonically
        eval_report = CanonicalEvaluationService.evaluate(problem, result.best_layout)
        assert eval_report.is_complete is True
        assert eval_report.is_feasible is True
        assert eval_report.hard_violations_count == 0


class TestZeroToleranceOutputValidator:
    """Verify zero-tolerance rejection of ungrounded financial claims, department counts, and percentages."""

    @pytest.fixture
    def base_payload(self):
        svc = ProblemService()
        problem = svc.load_problem(DATA_EXAMPLES_DIR / "sample_plant.json")
        return PayloadSanitizer.build_sanitized_payload(
            problem=problem,
            question_type=PresetQuestionType.WHY_FEASIBLE,
        )

    def test_validator_rejects_hallucinated_department_count(self, base_payload):
        explanation = StructuredAIExplanation(
            summary="Layout has 16 departments placed with optimal routing.",
            main_reasons=["High department density"],
            strengths=["Zero overlap"],
            risks=["Tight aisles"],
            trade_offs=["None"],
            limitations=["Heuristic only"],
            evidence_references=["area_utilization"],
        )
        passed, errors = ExplanationOutputValidator.validate(explanation, base_payload)
        assert passed is False
        assert any("Department count hallucination" in err for err in errors)

    def test_validator_rejects_hallucinated_percentage(self, base_payload):
        explanation = StructuredAIExplanation(
            summary="Layout achieves 98.5% floor space utilization perfectly.",
            main_reasons=["Tight packing"],
            strengths=["Zero overlap"],
            risks=["Tight aisles"],
            trade_offs=["None"],
            limitations=["Heuristic only"],
            evidence_references=["area_utilization"],
        )
        passed, errors = ExplanationOutputValidator.validate(explanation, base_payload)
        assert passed is False
        assert any("Ungrounded percentage detected" in err for err in errors)

    def test_validator_rejects_hallucinated_financial_dollar_amount(self, base_payload):
        explanation = StructuredAIExplanation(
            summary="Layout reduces material handling cost to $25,000 per month.",
            main_reasons=["Short path"],
            strengths=["Zero overlap"],
            risks=["Tight aisles"],
            trade_offs=["None"],
            limitations=["Heuristic only"],
            evidence_references=["material_handling_cost"],
        )
        passed, errors = ExplanationOutputValidator.validate(explanation, base_payload)
        assert passed is False
        assert any("Ungrounded financial figure detected" in err for err in errors)

    def test_validator_accepts_correctly_grounded_numbers(self, base_payload):
        # Sample plant has 10 departments and 91.67% utilization
        explanation = StructuredAIExplanation(
            summary=f"Layout packs {base_payload.department_count} departments with {base_payload.area_utilization_pct:.1f}% floor utilization.",
            main_reasons=["Slicing tree packing guarantees zero overlap"],
            strengths=["100% complete department containment"],
            risks=["Tight clearances"],
            trade_offs=["None"],
            limitations=["Heuristic boundaries apply"],
            evidence_references=["area_utilization"],
            global_optimality_disclaimer="Facility layout is NP-hard; no mathematical guarantee of global optimality.",
        )
        passed, errors = ExplanationOutputValidator.validate(explanation, base_payload)
        assert passed is True
        assert len(errors) == 0


class TestSecurityHardeningConsentStore:
    """Verify cryptographically signed single-use tokens, session binding, and replay prevention."""

    def test_consent_registration_and_single_use_consumption(self):
        p_hash = "abc123hash"
        token_str, expires = ServerConsentStore.register_consent(p_hash, client_session_id="sess_alpha")
        assert token_str is not None
        assert expires is not None

        # First consumption must succeed
        valid, err = ServerConsentStore.verify_and_consume(token_str, expected_payload_hash=p_hash, client_session_id="sess_alpha")
        assert valid is True
        assert err is None

        # Replay attempt with same token must fail with 403 / Security Violation
        valid_again, err_again = ServerConsentStore.verify_and_consume(token_str, expected_payload_hash=p_hash, client_session_id="sess_alpha")
        assert valid_again is False
        assert "Security Violation: Consent token has already been consumed" in err_again

    def test_session_mismatch_rejection(self):
        p_hash = "abc123hash"
        token_str, _ = ServerConsentStore.register_consent(p_hash, client_session_id="sess_legit")

        # Attempt to consume from an adversarial/different session ID
        valid, err = ServerConsentStore.verify_and_consume(token_str, expected_payload_hash=p_hash, client_session_id="sess_adversary")
        assert valid is False
        assert "Session mismatch" in err

    def test_tampered_payload_hash_rejection(self):
        p_hash = "abc123hash"
        token_str, _ = ServerConsentStore.register_consent(p_hash, client_session_id="sess_alpha")

        # Tampered expected hash
        valid, err = ServerConsentStore.verify_and_consume(token_str, expected_payload_hash="tampered_hash", client_session_id="sess_alpha")
        assert valid is False
        assert "Consent token hash mismatch" in err

    def test_tampered_token_signature_rejection(self):
        p_hash = "abc123hash"
        token_str, _ = ServerConsentStore.register_consent(p_hash, client_session_id="sess_alpha")

        # Tamper the token JSON content
        token_obj = json.loads(token_str)
        token_obj["payload_hash"] = "altered_hash"
        tampered_token_str = json.dumps(token_obj)

        valid, err = ServerConsentStore.verify_and_consume(tampered_token_str, expected_payload_hash="altered_hash", client_session_id="sess_alpha")
        assert valid is False
        assert "Invalid consent signature" in err

    def test_grant_consent_api_endpoint(self, client):
        req = {
            "payload_hash": "testhash123456",
            "client_session_id": "session_api_test",
            "consent_acknowledged": True,
            "opt_in_exact_dimensions": True,
            "opt_in_exact_areas": True,
            "opt_in_financial_costs": False,
        }
        res = client.post("/api/ai/grant-consent", json=req)
        assert res.status_code == 200
        data = res.json()
        assert data["single_use"] is True
        assert data["client_session_id"] == "session_api_test"
        assert data["payload_hash"] == "testhash123456"
        assert "consent_token" in data

        # Unchecked acknowledgment must fail with 400
        req_unchecked = dict(req, consent_acknowledged=False)
        res_fail = client.post("/api/ai/grant-consent", json=req_unchecked)
        assert res_fail.status_code == 400


class TestAPIResilienceAndErrorHandling:
    """Verify system resilience against malformed requests and unresolvable entities."""

    def test_unresolvable_problem_id_returns_404(self, client):
        res = client.post("/api/ai/explain-local", json={
            "problem_id": "NON_EXISTENT_FACTORY_999",
            "question_type": "why_strategy_selected",
        })
        assert res.status_code == 404
        assert "could not be resolved" in res.json()["detail"]

    def test_explain_gemini_without_prior_preview_returns_400(self, client):
        res = client.post("/api/ai/explain-gemini", json={
            "problem_id": "FLP_INDUSTRIAL_10",
            "question_type": "why_strategy_selected",
            "payload_hash": "fake_unmatched_hash",
            "consent_token": "fake_token",
            "client_session_id": "sess_test",
        })
        assert res.status_code == 400
        assert "Payload hash mismatch" in res.json()["detail"]
