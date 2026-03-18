"""
Core API and validation tests for the Maintenance Predictor.
Run with: pytest test_api.py -v
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
from models import Log, AnalysisResult
from datetime import datetime

# Use in-memory SQLite so tests stay isolated from the local development database.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    # Swap the app's normal database dependency for the in-memory test session.
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Reset database before each test."""
    # Recreate tables for every test so cases can run in any order.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(app)


class TestBasicEndpoints:
    """Test that basic API endpoints are reachable and return expected shapes."""

    def test_health_check(self):
        """GET / should return health status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ingest_csv(self):
        """POST /api/logs/ingest should load CSV and return ingested count."""
        response = client.post("/api/logs/ingest")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ingested"] == 1000
        assert "file" in data

    def test_get_machines(self):
        """GET /api/logs/machines returns list of machine IDs after ingestion."""
        client.post("/api/logs/ingest")
        response = client.get("/api/logs/machines")
        assert response.status_code == 200
        data = response.json()
        assert "machine_ids" in data
        assert len(data["machine_ids"]) > 0

    def test_get_logs_pagination(self):
        """GET /api/logs returns paginated logs."""
        client.post("/api/logs/ingest")
        response = client.get("/api/logs?page=1&page_size=50")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["total"] == 1000
        assert data["pages"] == 20
        assert len(data["logs"]) == 50

    def test_get_logs_with_machine_filter(self):
        """GET /api/logs?machine_id=MCH-01 filters by machine."""
        client.post("/api/logs/ingest")
        response = client.get("/api/logs?machine_id=MCH-01&page=1&page_size=50")
        assert response.status_code == 200
        data = response.json()
        # All returned logs should have machine_id=MCH-01
        for log in data["logs"]:
            assert log["machine_id"] == "MCH-01"


class TestIngestion:
    """Test CSV ingestion logic."""

    def test_ingestion_idempotency(self):
        """Running ingest twice should not create duplicates."""
        response1 = client.post("/api/logs/ingest")
        assert response1.json()["ingested"] == 1000

        response2 = client.post("/api/logs/ingest")
        assert response2.json()["ingested"] == 1000

        # Confirm we still have 1000, not 2000
        response_logs = client.get("/api/logs?page=1&page_size=50")
        assert response_logs.json()["total"] == 1000

    def test_ingestion_before_analysis_fails(self):
        """POST /api/analysis/run without ingestion should fail."""
        response = client.post("/api/analysis/run")
        assert response.status_code == 400
        assert "ingest" in response.json()["detail"].lower()


class TestAIAnalysisValidation:
    """Test the AI response validation logic."""

    def test_analysis_schema_strict(self):
        """
        Validate that the validator rejects incomplete or malformed schemas.
        This tests the _validate_response function indirectly via mocking.
        """
        from services.ai_service import _validate_response

        # Missing field
        invalid1 = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    # Missing 'reason' and 'affected_sensors'
                }
            ]
        }
        errors = _validate_response(invalid1)
        assert len(errors) > 0
        assert any("reason" in e.lower() for e in errors)

    def test_analysis_risk_level_strict(self):
        """Validator rejects invalid risk_level values."""
        from services.ai_service import _validate_response

        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "critical",  # Not in {high, medium, low}
                    "reason": "high failure rate",
                    "affected_sensors": ["temperature"],
                }
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("risk_level" in e.lower() for e in errors)

    def test_analysis_exact_3_items(self):
        """Validator enforces exactly 3 items in top_3_at_risk."""
        from services.ai_service import _validate_response

        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "high failure rate",
                    "affected_sensors": ["temperature"],
                }
                # Only 1 item, not 3
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("3" in e for e in errors)

    def test_contradiction_high_risk_normal_reason(self):
        """
        Validator catches contradiction: high risk but reason implies normal operation.
        """
        from services.ai_service import _validate_response

        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "all sensors normal, no anomalies detected",  # Normal language
                    "affected_sensors": ["temperature"],
                },
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "moderate vibration spike",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "minor temp variation",
                    "affected_sensors": ["temperature"],
                },
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("contradiction" in e.lower() for e in errors)

    def test_contradiction_low_risk_many_sensors(self):
        """
        Validator catches contradiction: low risk but >2 sensors affected.
        """
        from services.ai_service import _validate_response

        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "critical failure imminent",
                    "affected_sensors": ["temperature", "vibration"],
                },
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "moderate anomaly",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "minor issue",
                    "affected_sensors": ["temperature", "vibration", "status"],  # 3 sensors for low risk
                },
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("contradiction" in e.lower() for e in errors)

    def test_valid_response_passes(self):
        """
        A well-formed response should validate successfully.
        """
        from services.ai_service import _validate_response

        valid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-02",
                    "risk_level": "high",
                    "reason": "Repeated temperature spikes above 90°C with high vibration bursts",
                    "affected_sensors": ["temperature", "vibration"],
                },
                {
                    "machine_id": "MCH-04",
                    "risk_level": "medium",
                    "reason": "Elevated error count in recent logs",
                    "affected_sensors": ["status"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "Minor temperature drift, no other anomalies",
                    "affected_sensors": ["temperature"],
                },
            ]
        }
        errors = _validate_response(valid)
        assert len(errors) == 0


class TestAnalysisPersistence:
    """Test that analysis results are persisted and retrieved correctly."""

    def test_analysis_history_persists(self):
        """Running multiple analyses should accumulate in history."""
        # Ingest and run first analysis
        client.post("/api/logs/ingest")
        response1 = client.post("/api/analysis/run")
        assert response1.status_code == 200
        analysis_id_1 = response1.json()["id"]

        # Run another analysis
        response2 = client.post("/api/analysis/run")
        assert response2.status_code == 200
        analysis_id_2 = response2.json()["id"]

        # Get history
        history_response = client.get("/api/analysis/history")
        assert history_response.status_code == 200
        data = history_response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        # Newest should be first
        assert data["results"][0]["id"] == analysis_id_2

    def test_analysis_result_retrieval(self):
        """GET /api/analysis/{id} should return specific result."""
        client.post("/api/logs/ingest")
        response = client.post("/api/analysis/run")
        analysis_id = response.json()["id"]

        get_response = client.get(f"/api/analysis/{analysis_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == analysis_id
        assert data["status"] in ["success", "error"]

    def test_missing_analysis_returns_404(self):
        """GET /api/analysis/999 should return 404."""
        response = client.get("/api/analysis/999")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error paths and resilience."""

    def test_analysis_without_data_gives_clear_error(self):
        """Running analysis without ingestion gives clear, actionable error."""
        response = client.post("/api/analysis/run")
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "ingest" in error_detail.lower()
        assert "csv" in error_detail.lower()

    def test_invalid_pagination_params(self):
        """Invalid pagination params should be handled gracefully."""
        client.post("/api/logs/ingest")

        # page < 1 should fail per Query validation
        response = client.get("/api/logs?page=0&page_size=50")
        assert response.status_code == 422  # Validation error

        # page_size > 500 should fail
        response = client.get("/api/logs?page=1&page_size=1000")
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
