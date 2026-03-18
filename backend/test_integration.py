"""
Integration tests with mocked AI responses.
Shows how to test the complete pipeline without hitting the Anthropic API.

Run with: pytest test_integration.py -v
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from services.ai_service import run_analysis


def create_mock_response(text_content):
    """Helper to create a properly structured mock response."""
    # Anthropic responses expose content blocks; the tests mirror that shape.
    mock_msg = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text_content
    mock_msg.content = [mock_content]
    return mock_msg


class TestAISafetyRetry:
    """Test that the AI service retries on validation failures."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-sonnet-4-6"})
    @patch("services.ai_service.anthropic.Anthropic")
    def test_retry_on_malformed_json(self, mock_anthropic_class):
        """
        Simulate Claude returning non-JSON text, then valid JSON on retry.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        valid_response = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "Temperature spikes",
                    "affected_sensors": ["temperature"],
                },
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "Vibration anomaly",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "Minor drift",
                    "affected_sensors": ["status"],
                },
            ]
        }

        mock_client.messages.create.side_effect = [
            create_mock_response("This is not JSON at all"),
            create_mock_response('{"broken": "json"'),  # Incomplete JSON
            create_mock_response(json.dumps(valid_response)),
        ]

        # Minimal summary data is enough because the retry logic is the real target here.
        machine_summary = [{"machine_id": "MCH-01", "avg_temperature": 85.0}]
        result = run_analysis(machine_summary)

        # Should succeed on 3rd attempt after 2 failures
        assert result["status"] == "success"
        assert result["data"] is not None
        assert result["attempt_count"] == 3
        assert mock_client.messages.create.call_count == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-sonnet-4-6"})
    @patch("services.ai_service.anthropic.Anthropic")
    def test_validation_catches_contradiction(self, mock_anthropic_class):
        """
        Simulate Claude returning high risk but with normal reason.
        Should be rejected and retried.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        contradiction_response = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "All sensors normal, no issues",  # CONTRADICTION
                    "affected_sensors": ["temperature"],
                },
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "Moderate spike",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "Normal variance",
                    "affected_sensors": ["status"],
                },
            ]
        }

        valid_response = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-01",
                    "risk_level": "high",
                    "reason": "Temperature consistently above 95°C",
                    "affected_sensors": ["temperature"],
                },
                {
                    "machine_id": "MCH-02",
                    "risk_level": "medium",
                    "reason": "Vibration spike detected",
                    "affected_sensors": ["vibration"],
                },
                {
                    "machine_id": "MCH-03",
                    "risk_level": "low",
                    "reason": "Minor temperature drift",
                    "affected_sensors": ["status"],
                },
            ]
        }

        mock_client.messages.create.side_effect = [
            create_mock_response(json.dumps(contradiction_response)),
            create_mock_response(json.dumps(valid_response)),
        ]

        machine_summary = [{"machine_id": "MCH-01", "avg_temperature": 85.0}]
        result = run_analysis(machine_summary)

        # Should succeed on 2nd attempt after validation failure
        assert result["status"] == "success"
        assert result["attempt_count"] == 2
        assert mock_client.messages.create.call_count == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-sonnet-4-6"})
    @patch("services.ai_service.anthropic.Anthropic")
    def test_all_retries_exhausted_returns_error(self, mock_anthropic_class):
        """
        Simulate all 3 retries failing - should return error status.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_client.messages.create.side_effect = [
            create_mock_response("bad json 1"),
            create_mock_response("bad json 2"),
            create_mock_response("bad json 3"),
        ]

        machine_summary = [{"machine_id": "MCH-01", "avg_temperature": 85.0}]
        result = run_analysis(machine_summary)

        # Should fail after 3 attempts
        assert result["status"] == "error"
        assert result["data"] is None
        assert result["attempt_count"] == 3
        assert result["error_message"] is not None
        assert "failed after 3 attempts" in result["error_message"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-sonnet-4-6"})
    @patch("services.ai_service.anthropic.Anthropic")
    def test_successful_analysis_first_try(self, mock_anthropic_class):
        """
        Happy path: Claude returns valid JSON on first try.
        """
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        valid_response = {
            "top_3_at_risk": [
                {
                    "machine_id": "MCH-02",
                    "risk_level": "high",
                    "reason": "Repeated temperature spikes above 90°C with high vibration",
                    "affected_sensors": ["temperature", "vibration"],
                },
                {
                    "machine_id": "MCH-04",
                    "risk_level": "medium",
                    "reason": "Elevated error count in logs",
                    "affected_sensors": ["status"],
                },
                {
                    "machine_id": "MCH-01",
                    "risk_level": "low",
                    "reason": "Minor temperature variance within normal band",
                    "affected_sensors": ["temperature"],
                },
            ]
        }

        mock_client.messages.create.return_value = create_mock_response(json.dumps(valid_response))

        machine_summary = [
            {"machine_id": "MCH-01", "avg_temperature": 72.5},
            {"machine_id": "MCH-02", "avg_temperature": 88.2},
        ]
        result = run_analysis(machine_summary)

        # First attempt should succeed
        assert result["status"] == "success"
        assert result["data"] is not None
        assert result["attempt_count"] == 1
        assert len(result["data"]["top_3_at_risk"]) == 3
        assert result["data"]["top_3_at_risk"][0]["machine_id"] == "MCH-02"
        assert result["data"]["top_3_at_risk"][0]["risk_level"] == "high"


class TestErrorHandling:
    """Test error handling in AI service."""

    def test_no_api_key_returns_clear_error(self):
        """When ANTHROPIC_API_KEY is not set, should return helpful error."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            machine_summary = [{"machine_id": "MCH-01"}]
            result = run_analysis(machine_summary)

            assert result["status"] == "error"
            assert result["data"] is None
            assert "ANTHROPIC_API_KEY" in result["error_message"]

    # Generic exception handling is not duplicated here; the missing API key path
    # already proves the service can fail fast with a user-facing error message.



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
