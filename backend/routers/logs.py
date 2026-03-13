from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc
from typing import Optional
from database import get_db
from models import Log
from services.data_service import ingest_csv

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/ingest")
def ingest_logs(db: Session = Depends(get_db)):
    """Load the CSV file into the database. Safe to call multiple times (idempotent)."""
    try:
        result = ingest_csv(db)
        return {"success": True, **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("")
def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    machine_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return paginated logs, optionally filtered by machine_id."""
    query = db.query(Log).order_by(asc(Log.timestamp))

    if machine_id:
        query = query.filter(Log.machine_id == machine_id)

    total = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "machine_id": log.machine_id,
                "temperature": log.temperature,
                "vibration": log.vibration,
                "status": log.status,
            }
            for log in logs
        ],
    }


@router.get("/machines")
def get_machine_ids(db: Session = Depends(get_db)):
    """Return the list of unique machine IDs present in the logs."""
    from sqlalchemy import distinct
    ids = db.query(distinct(Log.machine_id)).order_by(Log.machine_id).all()
    return {"machine_ids": [r[0] for r in ids]}
