from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

# Pull DATABASE_URL from backend/.env when available.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maintenance.db")

# SQLite needs a thread-safety override for FastAPI's request handling model.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# SessionLocal is the per-request database session factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    # FastAPI dependency that opens a session for the request and always closes it.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
