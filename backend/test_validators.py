"""
Focused validator tests - no CSV required, fast execution.
These tests directly validate the most critical logic for the interview.

Run with: pytest test_validators.py -v
"""

import pytest
from services.ai_service import _validate_response


class TestJSONValidation:
    """Test strict JSON schema validation."""

    def test_valid_response_passes(self):
        """A well-formed response should validate successfully."""
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
        assert len(errors) == 0, f"Expected no errors, but got: {errors}"

    def test_not_dict_fails(self):
        """Response must be a dict, not a list or string."""
        errors = _validate_response([])
        assert len(errors) > 0
        assert any("object" in e.lower() for e in errors)

    def test_missing_top_3_at_risk_field(self):
        """Response must have 'top_3_at_risk' key."""
        invalid = {"wrong_key": []}
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("top_3_at_risk" in e for e in errors)

    def test_top_3_at_risk_not_array(self):
        """'top_3_at_risk' must be an array, not a dict or string."""
        invalid = {"top_3_at_risk": "not an array"}
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("array" in e.lower() for e in errors)

    def test_exactly_3_items_required(self):
        """Array must contain exactly 3 items."""
        # Too few entries should fail.
        invalid_few = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "failure",
                    "affected_sensors": ["temperature"],
                }
            ]
        }
        errors = _validate_response(invalid_few)
        assert len(errors) > 0
        assert any("3" in e for e in errors)

        # Too many entries should fail as well.
        invalid_many = {
            "top_3_at_risk": [
                {"machine_id": "MCH-01", "risk_level": "high", "reason": "x", "affected_sensors": ["temperature"]},
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
                {"machine_id": "MCH-04", "risk_level": "high", "reason": "w", "affected_sensors": ["temperature"]},
            ]
        }
        errors = _validate_response(invalid_many)
        assert len(errors) > 0


class TestRequiredFields:
    """Test that all required fields are present and correct."""

    def test_missing_machine_id(self):
        """Each item must have 'machine_id'."""
        invalid = {
            "top_3_at_risk": [
                {
                    # Missing machine_id
                    "risk_level": "high",
                    "reason": "test",
                    "affected_sensors": ["temperature"],
                },
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("machine_id" in e for e in errors)

    def test_missing_reason(self):
        """Each item must have 'reason'."""
        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    # Missing reason
                    "affected_sensors": ["temperature"],
                },
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("reason" in e.lower() for e in errors)

    def test_missing_affected_sensors(self):
        """Each item must have 'affected_sensors'."""
        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "test",
                    # Missing affected_sensors
                },
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("affected_sensors" in e for e in errors)


class TestRiskLevel:
    """Test that risk_level values are valid."""

    def test_invalid_risk_level(self):
        """risk_level must be 'high', 'medium', or 'low'."""
        for invalid_level in ["critical", "MEDIUM", "severe", 1, "unknown"]:
            response = {
                "top_3_at_risk": [
                    {
                        "machine_id": "MCH-01",
                        "risk_level": invalid_level,
                        "reason": "test",
                        "affected_sensors": ["temperature"],
                    },
                    {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                    {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
                ]
            }
            errors = _validate_response(response)
            assert len(errors) > 0, f"Expected errors for risk_level={invalid_level}"
            assert any("risk_level" in e for e in errors)

    def test_valid_risk_levels(self):
        """All valid risk levels should pass."""
        for level in ["high", "medium", "low"]:
            response = {
                "top_3_at_risk": [
                    {"machine_id": "MCH-01", "risk_level": level, "reason": "a", "affected_sensors": ["temperature"]},
                    {"machine_id": "MCH-02", "risk_level": "medium", "reason": "b", "affected_sensors": ["vibration"]},
                    {"machine_id": "MCH-03", "risk_level": "low", "reason": "c", "affected_sensors": ["status"]},
                ]
            }
            errors = _validate_response(response)
            # Should have no risk_level errors
            risk_errors = [e for e in errors if "risk_level" in e]
            assert len(risk_errors) == 0, f"Unexpected errors for valid risk_level={level}: {risk_errors}"


class TestAffectedSensors:
    """Test that affected_sensors contain only valid sensor names."""

    def test_affected_sensors_must_be_array(self):
        """affected_sensors must be an array."""
        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "test",
                    "affected_sensors": "temperature",  # Should be array
                },
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("array" in e.lower() for e in errors)

    def test_invalid_sensor_names(self):
        """Sensor names must be 'temperature', 'vibration', or 'status'."""
        invalid = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "test",
                    "affected_sensors": ["pressure", "humidity"],  # Invalid sensors
                },
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "y", "affected_sensors": ["vibration"]},
                {"machine_id": "MCH-03", "risk_level": "low", "reason": "z", "affected_sensors": ["status"]},
            ]
        }
        errors = _validate_response(invalid)
        assert len(errors) > 0
        assert any("sensor" in e.lower() for e in errors)

    def test_valid_sensor_names(self):
        """All valid sensor names should pass."""
        valid = {
            "top_3_at_risk": [
                {"machine_id": "MCH-01", "risk_level": "high", "reason": "a", "affected_sensors": ["temperature"]},
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "b", "affected_sensors": ["vibration"]},
                {
                    "machine_id": "MCH-03",
                    "risk_level": "high",  # Changed to high since it has 3 sensors
                    "reason": "multiple anomalies",
                    "affected_sensors": ["temperature", "vibration", "status"],
                },
            ]
        }
        errors = _validate_response(valid)
        # Filter to sensor-related errors
        sensor_errors = [e for e in errors if "sensor" in e.lower()]
        assert len(sensor_errors) == 0


class TestLogicalContradictions:
    """Test that contradictions between risk_level and reason are caught."""

    def test_high_risk_with_normal_reason_rejected(self):
        """
        High risk but reason implies everything is normal = logical contradiction.
        """
        # Mirror the phrases the validator treats as evidence of normal operation.
        normal_phrases = [
            "all sensors normal",
            "no anomalies",
            "operating normally",
            "no issues detected",
            "within normal range",
        ]

        for phrase in normal_phrases:
            response = {
                "top_3_at_risk": [
                    {
                        "machine_id": "MCH-01",
                        "risk_level": "high",
                        "reason": f"Everything is {phrase}",
                        "affected_sensors": ["temperature"],
                    },
                    {
                        "machine_id": "MCH-02",
                        "risk_level": "medium",
                        "reason": "actual issue",
                        "affected_sensors": ["vibration"],
                    },
                    {
                        "machine_id": "MCH-03",
                        "risk_level": "low",
                        "reason": "minor drift",
                        "affected_sensors": ["status"],
                    },
                ]
            }
            errors = _validate_response(response)
            assert len(errors) > 0, f"Expected contradiction error for phrase: {phrase}"
            assert any("contradiction" in e.lower() for e in errors)

    def test_low_risk_with_many_sensors_rejected(self):
        """
        Low risk but 3+ sensors affected = logical contradiction.
        """
        response = {
            "top_3_at_risk": [
                {"machine_id": "MCH-01", "risk_level": "high", "reason": "critical", "affected_sensors": ["temperature"]},
                {"machine_id": "MCH-02", "risk_level": "medium", "reason": "moderate", "affected_sensors": ["vibration"]},
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "minor drift",
                    "affected_sensors": ["temperature", "vibration", "status"],  # 3 sensors for low risk
                },
            ]
        }
        errors = _validate_response(response)
        assert len(errors) > 0
        assert any("contradiction" in e.lower() for e in errors)

    def test_low_risk_with_2_sensors_ok(self):
        """Low risk with 2 sensors should pass (threshold is >2)."""
        response = {
            "top_3_at_risk": [
                {"machine_id": "MCH-01", "risk_level": "high", "reason": "critical", "affected_sensors": ["temperature"]},
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "moderate",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "minor issues",
                    "affected_sensors": ["temperature", "vibration"],  # OK: exactly 2
                },
            ]
        }
        errors = _validate_response(response)
        # Should only fail if there are other issues
        contradiction_errors = [e for e in errors if "contradiction" in e.lower()]
        assert len(contradiction_errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
