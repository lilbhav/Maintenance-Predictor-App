# IoT Maintenance Insight Dashboard

A full-stack application that processes industrial sensor logs, stores them in SQLite, and uses **Anthropic Claude** to identify the top 3 at-risk machines with a validation/retry layer.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy · SQLite |
| AI Engine | Anthropic Claude (`claude-sonnet-4-6` default, configurable via `ANTHROPIC_MODEL` and optional `ANTHROPIC_MODELS`) |
| Frontend | React 18 · Vite · Tailwind CSS · TypeScript |

---

## Clone and Setup 

### Prerequisites

- Git
- Python 3.9+
- Node.js 18+ (includes npm)

### 1. Clone the repository

```bash
git clone https://github.com/lilbhav/Maintenance-Predictor-App.git
cd Maintenance-Predictor-App
```

### 2. Configure backend environment

```bash
cd backend
copy .env.example .env
```

Then edit `.env` and set `ANTHROPIC_API_KEY`.

### 3. Backend

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows (cmd)
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Start server
# Use the provided script which handles PATH automatically:
start.bat
```

The API will be available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

If you see a Windows `_sqlite3` DLL error while running tests or starting backend manually:

```powershell
$env:PATH = "C:\Users\chavab\anaconda3\Library\bin;$env:PATH"
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev        # or: start.bat
```

The UI will be available at **http://localhost:5173**

### 5. Optional: run tests

```powershell
cd backend
$env:PATH = "C:\Users\chavab\anaconda3\Library\bin;$env:PATH"
pytest test_validators.py test_integration.py test_api.py -v
```

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
├── README.md
├── README_AI.md
├── data/
│   └── manufacturing_floor_logs_1000.csv
├── backend/
│   ├── main.py                  # FastAPI app + CORS + lifespan
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # Log + AnalysisResult ORM models
│   ├── routers/
│   │   ├── logs.py              # /api/logs endpoints
│   │   └── analysis.py          # /api/analysis endpoints
│   ├── services/
│   │   ├── data_service.py      # CSV ingestion + per-machine aggregation
│   │   └── ai_service.py        # Claude client + validation + retry logic
│   ├── test_api.py              # API and endpoint behavior tests
│   ├── test_validators.py       # AI response validation unit tests
│   ├── test_integration.py      # Retry/error handling integration tests
│   ├── requirements.txt
│   ├── .env.example
│   └── start.bat                # Windows convenience launcher
└── frontend/
    ├── index.html
    ├── src/
    │   ├── api/client.ts        # Typed API wrappers
    │   ├── pages/
    │   │   ├── Dashboard.tsx    # Logs table + AI analysis trigger
    │   │   └── Trends.tsx       # Historical analysis list
    │   └── components/
    │       ├── Navbar.tsx
    │       ├── LogsTable.tsx
    │       └── HealthStatusCard.tsx
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── package.json
    └── start.bat
```