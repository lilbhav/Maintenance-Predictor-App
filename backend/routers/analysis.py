import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AnalysisResult
from services.data_service import get_machine_summary
from services.ai_service import run_analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/run")
def run_analysis_endpoint(db: Session = Depends(get_db)):
    """
    Aggregate log data, send to AI, validate response with retries,
    persist the result, and return it.
    """
    summary = get_machine_summary(db)
    if not summary:
        raise HTTPException(
            status_code=400,
            detail="No log data found. Please ingest the CSV first via POST /api/logs/ingest.",
        )

    result = run_analysis(summary)

    record = AnalysisResult(
        top_machines=json.dumps(result["data"]) if result["data"] else None,
        raw_prompt=result.get("raw_prompt", ""),
        status=result["status"],
        error_message=result.get("error_message"),
        attempt_count=result.get("attempt_count", 1),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "status": record.status,
        "attempt_count": record.attempt_count,
        "error_message": record.error_message,
        "top_machines": result["data"],
    }


@router.get("/history")
def get_analysis_history(db: Session = Depends(get_db)):
    """Return all past analysis results, newest first."""
    records = db.query(AnalysisResult).order_by(desc(AnalysisResult.created_at)).all()
    return {
        "total": len(records),
        "results": [_serialize(r) for r in records],
    }


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Return a specific analysis result by ID."""
    record = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis result not found.")
    return _serialize(record)


def _serialize(record: AnalysisResult) -> dict:
    top = None
    if record.top_machines:
        try:
            top = json.loads(record.top_machines)
        except json.JSONDecodeError:
            top = None
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat(),
        "status": record.status,
        "attempt_count": record.attempt_count,
        "error_message": record.error_message,
        "top_machines": top,
    }
