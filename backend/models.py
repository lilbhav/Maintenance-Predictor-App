from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Log(Base):
    # Raw machine telemetry ingested from the manufacturing CSV.
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    machine_id = Column(String(20), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    vibration = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)


class AnalysisResult(Base):
    # Persisted record of each AI analysis attempt and its final outcome.
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    top_machines = Column(Text, nullable=True)   # JSON string
    raw_prompt = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="success")  # "success" | "error"
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=1)
