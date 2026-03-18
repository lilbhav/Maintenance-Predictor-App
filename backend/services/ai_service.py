import json
import logging
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# Try explicit configuration first, then fall back to known model IDs.
DEFAULT_MODEL_CANDIDATES = [
    "claude-sonnet-4-6",
    "claude-3-7-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
]


def _unique_keep_order(values: list[str]) -> list[str]:
    # Preserve the first occurrence of each non-empty model name.
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _get_candidate_models() -> list[str]:
    # Support either one preferred model or a comma-separated fallback list from .env.
    explicit_model = os.getenv("ANTHROPIC_MODEL", "").strip()
    extra_models_raw = os.getenv("ANTHROPIC_MODELS", "")
    extra_models = [m.strip() for m in extra_models_raw.split(",") if m.strip()]

    return _unique_keep_order([explicit_model, *extra_models, *DEFAULT_MODEL_CANDIDATES])

SYSTEM_PROMPT = """
You will be given aggregated sensor statistics for a set of machines on a manufacturing floor.
Your job is to identify the TOP 3 machines most at risk of failure.

You MUST respond with ONLY valid JSON, no prose, no markdown fences, no explanations outside the JSON object.

The response schema is:
{
  "top_3_at_risk": [
    {
      "machine_id": "<string>",
      "risk_level": "<high|medium|low>",
      "reason": "<concise explanation of why this machine is at risk>",
      "affected_sensors": ["<temperature|vibration|status>"]
    }
  ]
}

Rules:
- The array must contain EXACTLY 3 machines, ordered by risk (highest first).
- risk_level must be exactly "high", "medium", or "low" (lowercase).
- If a machine has a high risk_level its reason MUST describe a specific anomaly.
- affected_sensors must only contain values from: ["temperature", "vibration", "status"].
"""


def _build_user_message(machine_summary: list[dict], extra_context: str = "") -> str:
    # Keep the prompt payload machine-readable so retries can tighten the request.
    summary_json = json.dumps(machine_summary, indent=2)
    msg = f"Analyze the following machine summary data and return the top 3 at-risk machines:\n\n{summary_json}"
    if extra_context:
        msg += f"\n\nPrevious response was invalid. Error details:\n{extra_context}\nPlease fix and return valid JSON only."
    return msg


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_RISK_LEVELS = {"high", "medium", "low"}
VALID_SENSORS = {"temperature", "vibration", "status"}

NORMAL_PHRASES = [
    "all sensors normal",
    "no anomalies",
    "operating normally",
    "no issues detected",
    "within normal range",
    "all readings normal",
]


def _validate_response(data: Any) -> list[str]:
    """
    Returns a list of validation error strings.
    An empty list means the response is valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        errors.append("Response must be a JSON object.")
        return errors

    top3 = data.get("top_3_at_risk")
    if not isinstance(top3, list):
        errors.append("'top_3_at_risk' must be a JSON array.")
        return errors

    if len(top3) != 3:
        errors.append(f"'top_3_at_risk' must contain exactly 3 items, got {len(top3)}.")

    for i, item in enumerate(top3):
        prefix = f"Item {i + 1}"

        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be a JSON object.")
            continue

        for required_field in ("machine_id", "risk_level", "reason", "affected_sensors"):
            if required_field not in item:
                errors.append(f"{prefix}: missing required field '{required_field}'.")

        # Validate the schema first, then check for simple domain contradictions.
        risk = item.get("risk_level", "")
        if risk not in VALID_RISK_LEVELS:
            errors.append(
                f"{prefix}: 'risk_level' must be one of {sorted(VALID_RISK_LEVELS)}, got '{risk}'."
            )

        sensors = item.get("affected_sensors", [])
        if not isinstance(sensors, list):
            errors.append(f"{prefix}: 'affected_sensors' must be an array.")
        else:
            invalid = [s for s in sensors if s not in VALID_SENSORS]
            if invalid:
                errors.append(
                    f"{prefix}: invalid sensor(s) {invalid}. Allowed: {sorted(VALID_SENSORS)}."
                )

            # Logical contradiction: low risk but many affected sensors
            if risk == "low" and len(sensors) > 2:
                errors.append(
                    f"{prefix}: logical contradiction — risk_level is 'low' but "
                    f"{len(sensors)} sensors are listed as affected."
                )

        # Logical contradiction: high risk but reason implies no problem
        reason = item.get("reason", "").lower()
        if risk == "high" and any(phrase in reason for phrase in NORMAL_PHRASES):
            errors.append(
                f"{prefix}: logical contradiction — risk_level is 'high' but reason "
                f"implies normal operation: '{item.get('reason')}'."
            )

    return errors


def _extract_json(text: str) -> Any:
    """Try to parse JSON from an LLM response that may have surrounding text."""
    text = text.strip()

    # Strip common markdown wrappers before attempting JSON parsing.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some model responses include extra prose; salvage the first JSON object if possible.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_analysis(machine_summary: list[dict]) -> dict:
    """
    Send machine summary to Claude, validate response, retry up to MAX_RETRIES times.

    Returns:
        {
            "status": "success" | "error",
            "data": <parsed + validated response dict> | None,
            "raw_prompt": <last user prompt sent>,
            "attempt_count": <int>,
            "error_message": <str> | None,
        }
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "status": "error",
            "data": None,
            "raw_prompt": "",
            "attempt_count": 0,
            "error_message": "ANTHROPIC_API_KEY is not set. Please add it to backend/.env.",
        }

    client = anthropic.Anthropic(api_key=api_key)

    # Rotate through configured model IDs when the primary one is unavailable.
    candidate_models = _get_candidate_models()
    if not candidate_models:
        return {
            "status": "error",
            "data": None,
            "raw_prompt": "",
            "attempt_count": 0,
            "error_message": "No Anthropic model candidates available. Set ANTHROPIC_MODEL in backend/.env.",
        }

    extra_context = ""
    last_prompt = ""
    model_index = 0
    active_model = candidate_models[model_index]
    models_tried: list[str] = []

    attempt = 1
    while attempt <= MAX_RETRIES:
        # Feed back parse and validation failures so the next attempt can self-correct.
        user_message = _build_user_message(machine_summary, extra_context)
        last_prompt = user_message

        try:
            logger.info(
                "Calling Claude (attempt %d/%d) with model '%s'…",
                attempt,
                MAX_RETRIES,
                active_model,
            )
            response = client.messages.create(
                model=active_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            models_tried.append(active_model)
            raw_text = response.content[0].text

            try:
                parsed = _extract_json(raw_text)
            except (json.JSONDecodeError, ValueError) as exc:
                # Retry with the parse failure attached to the next prompt.
                extra_context = f"Your response was not valid JSON: {exc}\nRaw response was:\n{raw_text[:500]}"
                logger.warning("Attempt %d — JSON parse error: %s", attempt, exc)
                attempt += 1
                continue

            validation_errors = _validate_response(parsed)
            if validation_errors:
                # Retry when the JSON is structurally valid but fails domain rules.
                extra_context = "Validation errors found:\n" + "\n".join(
                    f"  - {e}" for e in validation_errors
                )
                logger.warning("Attempt %d — Validation errors: %s", attempt, validation_errors)
                attempt += 1
                continue

            logger.info("Attempt %d — Success.", attempt)
            return {
                "status": "success",
                "data": parsed,
                "raw_prompt": last_prompt,
                "attempt_count": attempt,
                "error_message": None,
            }

        except anthropic.APIError as exc:
            models_tried.append(active_model)
            error_text = str(exc)
            if "not_found_error" in error_text and model_index + 1 < len(candidate_models):
                model_index += 1
                active_model = candidate_models[model_index]
                extra_context = (
                    f"Model unavailable: {error_text}. "
                    f"Retrying with fallback model '{active_model}'."
                )
                logger.warning(
                    "Model not found. Switching to fallback model '%s'.", active_model
                )
                # Keep the same attempt count when only switching model IDs.
                continue

            error_msg = f"Anthropic API error on attempt {attempt}: {exc}"
            logger.error(error_msg)
            extra_context = error_msg
            attempt += 1
            continue

    # All retries exhausted
    tried_models_str = ", ".join(_unique_keep_order(models_tried)) if models_tried else "none"
    final_error = (
        f"Analysis failed after {MAX_RETRIES} attempts. Last error: {extra_context}. "
        f"Models tried: {tried_models_str}. "
        "Set ANTHROPIC_MODEL (or ANTHROPIC_MODELS) in backend/.env to a model your account can access."
    )
    logger.error(final_error)
    return {
        "status": "error",
        "data": None,
        "raw_prompt": last_prompt,
        "attempt_count": MAX_RETRIES,
        "error_message": final_error,
    }
