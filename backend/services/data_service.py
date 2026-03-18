import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from models import Log


BACKEND_DIR = Path(__file__).resolve().parents[1]
# Default to the workspace data folder so local startup works without extra config.
DEFAULT_CSV_PATH = BACKEND_DIR.parent / "data" / "manufacturing_floor_logs_1000.csv"


def _resolve_csv_path() -> Path:
    # Allow overrides from .env while keeping relative paths anchored to backend/.
    configured = os.getenv("CSV_FILE_PATH", "").strip()
    if not configured:
        return DEFAULT_CSV_PATH

    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path

    # Resolve relative CSV_FILE_PATH from backend root for predictable startup behavior.
    return (BACKEND_DIR / configured_path).resolve()


def ingest_csv(db: Session) -> dict:
    """
    Read the manufacturing CSV and upsert all rows into the logs table.
    Idempotent: clears existing rows first then re-inserts so this is safe to call multiple times.
    """
    csv_path = _resolve_csv_path()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at: {csv_path}")

    # Normalize column names so CSV formatting differences are less fragile.
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df.columns = [c.strip().lower() for c in df.columns]

    # Idempotent — truncate & reload
    db.query(Log).delete()
    db.commit()

    records = []
    for _, row in df.iterrows():
        # Convert each CSV row into the ORM shape expected by the logs table.
        records.append(
            Log(
                timestamp=row["timestamp"].to_pydatetime(),
                machine_id=str(row["machine_id"]).strip(),
                temperature=float(row["temperature"]),
                vibration=float(row["vibration"]),
                status=str(row["status"]).strip(),
            )
        )

    db.bulk_save_objects(records)
    db.commit()
    return {"ingested": len(records), "file": csv_path.name}


def get_machine_summary(db: Session) -> list[dict]:
    """
    Aggregate per-machine stats from the logs table for use in the AI prompt.
    """
    from sqlalchemy import func as sqlfunc, case
    from models import Log

    # Reduce raw logs to the key metrics the AI prompt needs per machine.
    rows = (
        db.query(
            Log.machine_id,
            sqlfunc.count(Log.id).label("total_logs"),
            sqlfunc.avg(Log.temperature).label("avg_temp"),
            sqlfunc.max(Log.temperature).label("max_temp"),
            sqlfunc.min(Log.temperature).label("min_temp"),
            sqlfunc.avg(Log.vibration).label("avg_vib"),
            sqlfunc.max(Log.vibration).label("max_vib"),
            sqlfunc.sum(case((Log.status == "ERROR", 1), else_=0)).label("error_count"),
            sqlfunc.sum(case((Log.status == "WARNING", 1), else_=0)).label("warning_count"),
            sqlfunc.sum(case((Log.status == "OPERATIONAL", 1), else_=0)).label("operational_count"),
        )
        .group_by(Log.machine_id)
        .order_by(Log.machine_id)
        .all()
    )

    return [
        {
            "machine_id": r.machine_id,
            "total_logs": r.total_logs,
            "avg_temperature": round(r.avg_temp, 2),
            "max_temperature": round(r.max_temp, 2),
            "min_temperature": round(r.min_temp, 2),
            "avg_vibration": round(r.avg_vib, 4),
            "max_vibration": round(r.max_vib, 4),
            "error_count": r.error_count,
            "warning_count": r.warning_count,
            "operational_count": r.operational_count,
        }
        for r in rows
    ]
