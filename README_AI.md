# AI Usage Notes (Interview Version)

I used GitHub Copilot to assist with implementation.

## 1. Prompts I Used

These are the main prompts I used:

1. Build a FastAPI backend with:
- CSV ingestion endpoint
- AI analysis endpoint
- SQLite + SQLAlchemy setup
- CORS for Vite frontend

2. Create database models for:
- logs
- analysis_results

3. Write a CSV ingestion service using pandas that is safe to run multiple times.

4. Write a machine summary query (avg/max/min temp, vibration, status counts).

5. Build an AI service that:
- sends data to Claude
- expects strict JSON output
- retries up to 3 times
- validates the AI response

6. Build React frontend pieces:
- typed API client
- dashboard page
- trends/history page
- logs table
- health status card

## 1.2 Debugging Prompts I Used (Most Useful)

These are the prompts I used when behavior did not match requirements and I needed to diagnose quickly:

1. "Given this FastAPI endpoint and SQLite setup, why would Windows throw `ImportError: DLL load failed while importing _sqlite3` and what is the safest fix?"

2. "Write pytest tests for an AI JSON validator that enforces exactly 3 machines, strict risk enums, and contradiction checks."

3. "Given this Claude response text, extract only the JSON payload safely, including cases where JSON is wrapped in markdown fences."

4. "Design retry logic for LLM calls: retry on malformed JSON or schema violations up to 3 times, and persist an error record if all retries fail."

5. "Review this TypeScript API type and React component props for mismatch bugs between nested and flat arrays."

6. "For a paginated table with filters, what state reset rules prevent stale page bugs after filter changes?"


## 1.1 Prompt-to-File Mapping

Below is the mapping between each prompt and the files it generated (or primarily produced).

1. Build a FastAPI backend with CSV ingestion, AI analysis, SQLite + SQLAlchemy, and CORS
- `backend/main.py`
- `backend/database.py`
- `backend/routers/logs.py`
- `backend/routers/analysis.py`
- `backend/requirements.txt`

2. Create database models for logs and analysis_results
- `backend/models.py`

3. Write a CSV ingestion service using pandas that is safe to run multiple times
- `backend/services/data_service.py`
- wired through `backend/routers/logs.py`

4. Write a machine summary query (avg/max/min temp, vibration, status counts)
- `backend/services/data_service.py` (aggregation logic)

5. Build an AI service that sends data to Claude, enforces strict JSON, retries up to 3 times, and validates responses
- `backend/services/ai_service.py`
- integrated in `backend/routers/analysis.py`

6. Build React frontend pieces (typed API client, dashboard page, trends/history page, logs table, health status card)
- `frontend/src/api/client.ts`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Trends.tsx`
- `frontend/src/components/LogsTable.tsx`
- `frontend/src/components/HealthStatusCard.tsx`
- supporting shell/navigation: `frontend/src/App.tsx`, `frontend/src/components/Navbar.tsx`

## 2. How I Verified the AI Output

1. Ran the app end-to-end:
- Ingest CSV
- Load logs
- Run AI analysis
- Confirm response renders in the UI

2. Manually tested edge cases in the AI response validator:
- wrong number of machines
- invalid risk values
- contradictory risk/reason combinations

3. Verified data shape consistency:
- backend response vs frontend TypeScript types

4. Verified retry behavior:
- forced error paths and confirmed attempt counts and error handling

5. Verified persistence behavior:
- successful analyses are stored with `status=success`
- failed analyses (after retries) are stored with `status=error`

6. Verified assignment-specific constraints explicitly:
- AI output is structured JSON with required keys
- exactly 3 at-risk machines are returned
- contradiction checks are enforced before saving

## 3. What I Fixed Manually

Main fixes I made after AI generation:

1. Made CSV ingestion truly idempotent by clearing old logs before reinsert.

2. Fixed frontend type mismatch for top_machines (nested object vs flat array).

3. Added SQLite threading config (check_same_thread) for FastAPI usage.

4. Improved JSON extraction from AI output to handle multi-line JSON.

5. Added safe handling when analysis returns no data (error path).

6. Improved UI behavior:
- hide pagination when only one page
- reset page to 1 when changing machine filter

---

## 4. Automated Test Suite (39 Tests)

To demonstrate code quality and the robustness of the AI-hard validation layer, I created a comprehensive test suite with **39 passing tests**.

### Quick Start

```powershell
# Set PATH for SQLite support, then run all tests
$env:PATH = "C:\Users\chavab\anaconda3\Library\bin;$env:PATH"
cd backend
pytest test_validators.py test_integration.py test_api.py -v
```

**Result: 39/39 tests pass** 

### Test Files

**test_validators.py (16 tests)** — Core AI response validation logic
- **JSON Structure Validation** (5 tests): Ensures response is well-formed dict with exactly 3 items
- **Required Fields** (3 tests): All required keys present in each item
- **Risk Level Values** (2 tests): Only `high`, `medium`, or `low` allowed
- **Affected Sensors** (3 tests): Valid sensor names only (`temperature`, `vibration`, `status`)
- **Logical Contradictions** (3 tests): Catches contradictory risk levels vs. reasons
  - High risk + "all sensors normal" reason → REJECTED
  - Low risk + 3+ affected sensors → REJECTED
  - Low risk + 2 sensors → ACCEPTED (threshold is >2)

**test_integration.py (5 tests)** — Retry logic and error handling with mocked Claude API
- **Retry on Validation Failure** (4 tests):
  - Malformed JSON → retry until success
  - Logical contradiction → reject & retry
  - All 3 retries fail → error status
  - Valid response on first try → success
- **Error Handling** (1 test):
  - Missing API key → clear error message

**test_api.py (18 tests)** — End-to-end API behavior and persistence
- Health and ingestion endpoints
- Pagination and machine filter behavior
- Analysis history and single-result retrieval
- Error paths (analysis before ingestion, invalid pagination)

### What These Tests Prove

**Schema Strictness**: AI responses must have exact structure or fail validation  
**Retry Logic**: Bad responses are rejected and retried up to 3 times  
**Contradiction Detection**: contradictions between risk level and reason are caught  
**Error Resilience**: Missing API key returns helpful message, app doesn't crash  

### Running Tests

**Demo:**
```powershell
# Verify tests pass (shows code quality)
$env:PATH = "C:\Users\chavab\anaconda3\Library\bin;$env:PATH"
cd backend
pytest test_validators.py test_integration.py test_api.py -v
```

### Windows-Specific Runtime Note

On this machine, SQLite required adding Anaconda's DLL folder to `PATH` before running tests/server:

```powershell
$env:PATH = "C:\Users\chavab\anaconda3\Library\bin;$env:PATH"
```

Without that, Python may fail with `_sqlite3` DLL load errors even when dependencies are installed.

### Why These Tests Matter

The assignment emphasizes an "AI-Hard" validation layer. These tests demonstrate that the implementation:
- **Never accepts malformed AI responses** — validators are strict about JSON schema
- **Automatically retries on validation failures** — up to 3 attempts before error
- **Detects logical contradictions** — catches cases like "high risk" but "normal operation"
- **Gracefully handles errors** — clear messages, no crashes, failed analyses are persisted