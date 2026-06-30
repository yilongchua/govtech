from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.storage import ensure_data_dirs
from backend.app.api.routes_jobs import router as jobs_router
from backend.app.api.routes_model_settings import router as model_settings_router
from backend.app.api.routes_syllabus import router as syllabus_router
from backend.app.api.routes_upload import router as upload_router

app = FastAPI(title="Exam Paper Alignment Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "supported_routes": ["configured_generic_subject"], "default_syllabus_year": settings.history_syllabus_year}


app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(syllabus_router)
app.include_router(model_settings_router)
