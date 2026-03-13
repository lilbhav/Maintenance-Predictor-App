import pandas as pd
import os
from datetime import datetime
from sqlalchemy.orm import Session
from models import Log


CSV_PATH = os.getenv(
    "CSV_FILE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "manufacturing_floor_logs_1000.csv"),
)


def ingest_csv(db: Session) -> dict:
    """
    Read the manufacturing CSV and upsert all rows into the logs table.
    Idempotent: clears existing rows first then re-inserts so this is safe to call multiple times.
    """
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    df.columns = [c.strip().lower() for c in df.columns]

    # Idempotent — truncate & reload
    db.query(Log).delete()
    db.commit()

    records = []
    for _, row in df.iterrows():
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
    return {"ingested": len(records), "file": os.path.basename(CSV_PATH)}


def get_machine_summary(db: Session) -> list[dict]:
    """
    Aggregate per-machine stats from the logs table for use in the AI prompt.
    """
    from sqlalchemy import func as sqlfunc, case
    from models import Log

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
