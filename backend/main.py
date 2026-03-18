import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables before importing modules that read configuration.
load_dotenv()

from database import engine, Base
from routers import logs, analysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the local database schema exists before the API starts serving traffic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="IoT Maintenance Insight Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(analysis.router)


@app.get("/")
def health():
    # Lightweight health endpoint used by tests and local startup checks.
    return {"status": "ok", "service": "IoT Maintenance Insight Dashboard"}
