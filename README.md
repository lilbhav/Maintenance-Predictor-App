# IoT Maintenance Insight Dashboard

A full-stack application that processes industrial sensor logs, stores them in SQLite, and uses **Anthropic Claude** to identify the top 3 at-risk machines with a validation/retry layer.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy · SQLite |
| AI Engine | Anthropic Claude (`claude-3-5-sonnet-20241022`) |
| Frontend | React 18 · Vite · Tailwind CSS · TypeScript |

---

## Quick Start

### 1. Backend

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows (cmd)
.venv\Scripts\activate.bat

# Copy & fill in your API key
copy .env.example .env
# Edit .env → set ANTHROPIC_API_KEY=sk-ant-...

# Install dependencies
pip install -r requirements.txt

# Start server  (add Anaconda Library/bin to PATH if on Anaconda Python)
# Use the provided script which handles PATH automatically:
start.bat
# OR manually:
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # or: start.bat
```

The UI will be available at **http://localhost:5173**

---

## Usage

1. Open **http://localhost:5173**
2. Click **Ingest CSV** — loads all 1,000 logs from `data/manufacturing_floor_logs_1000.csv` into SQLite
3. Browse sensor logs with pagination and machine filter
4. Click **Run AI Analysis** — Claude analyses aggregated sensor data, returns the top 3 at-risk machines, results are saved to DB and displayed as a Health Status card
5. Navigate to **Trends** to see all historical analysis runs

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/logs/ingest` | Ingest CSV → SQLite (idempotent) |
| `GET` | `/api/logs` | Paginated logs (`?page=&page_size=&machine_id=`) |
| `GET` | `/api/logs/machines` | Unique machine ID list |
| `POST` | `/api/analysis/run` | Run AI analysis, validate, save |
| `GET` | `/api/analysis/history` | All past results (newest first) |
| `GET` | `/api/analysis/{id}` | Single analysis result |

---

## AI Response Schema

```json
{
  "top_3_at_risk": [
    {
      "machine_id": "MCH-02",
      "risk_level": "high",
      "reason": "Repeated temperature spikes above 90°C with high vibration bursts",
      "affected_sensors": ["temperature", "vibration"]
    }
  ]
}
```

### Validation Layer

The AI service validates every Claude response before saving:

- JSON must parse successfully
- `top_3_at_risk` must be an array of exactly 3 items
- Each item requires: `machine_id`, `risk_level`, `reason`, `affected_sensors`
- `risk_level` must be `"high"`, `"medium"`, or `"low"`
- **Logical contradiction check 1**: `risk_level = "high"` but reason implies everything is normal → rejected
- **Logical contradiction check 2**: `risk_level = "low"` but > 2 sensors listed as affected → rejected
- On failure: up to **3 retries**, injecting the specific error back into the prompt
- On 3rd failure: stores an error row in `analysis_results` with `status = "error"`

---

## Project Structure

```
Maintenance-Predictor-App/
├── data/
│   └── manufacturing_floor_logs_1000.csv
├── backend/
│   ├── main.py                  # FastAPI app + CORS + lifespan
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # Log + AnalysisResult ORM models
│   ├── routers/
│   │   ├── logs.py              # /api/logs endpoints
│   │   └── analysis.py         # /api/analysis endpoints
│   ├── services/
│   │   ├── data_service.py      # CSV ingestion + per-machine aggregation
│   │   └── ai_service.py        # Claude client + validation + retry logic
│   ├── requirements.txt
│   ├── .env.example
│   └── start.bat                # Windows convenience launcher
└── frontend/
    ├── src/
    │   ├── api/client.ts        # Typed API wrappers
    │   ├── pages/
    │   │   ├── Dashboard.tsx    # Logs table + AI analysis trigger
    │   │   └── Trends.tsx       # Historical analysis list
    │   └── components/
    │       ├── Navbar.tsx
    │       ├── LogsTable.tsx
    │       └── HealthStatusCard.tsx
    ├── package.json
    └── start.bat
```
Application to process and analyze sensor logs
