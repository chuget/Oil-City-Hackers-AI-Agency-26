"""
Run from repo app root (Oil-City-Hackers-AI-Agency-26):

  uvicorn monitor_site.server:app --reload --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "web" / ".env", override=False)
os.chdir(ROOT)

from monitor_dashboard import build_dashboard_payload

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Public Contract Change Monitor", version="1.0.0")


@app.middleware("http")
async def no_cache_for_dashboard_assets(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/api/health")
def api_health() -> dict:
    """Lightweight check: can we load contract rows (DB or CSV)?"""
    try:
        from monitor_core import db_config_present, load_contracts

        df, src = load_contracts()
        return {
            "ok": True,
            "load_source": src,
            "rows_loaded": int(len(df)),
            "database_config_present": db_config_present(),
            "database_env_names_checked": ["DB_CONNECTION_STRING", "DATABASE_URL"],
            "env_files_checked": [str(ROOT / ".env"), str(ROOT / "web" / ".env")],
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "load_source": "",
                "rows_loaded": 0,
                "error": str(e),
            },
        )


@app.get("/api/bootstrap")
def api_bootstrap() -> dict:
    try:
        payload = build_dashboard_payload(10_000.0, "(all)", "(all)", None)
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "filter_departments": ["(all)"],
                "filter_procedures": ["(all)"],
                "rows_loaded": 0,
                "load_source": "",
                "error": str(e),
            },
        )
    return jsonable_encoder(
        {
            "filter_departments": payload.get("filter_departments", []),
            "filter_procedures": payload.get("filter_procedures", []),
            "rows_loaded": payload.get("rows_loaded", 0),
            "load_source": payload.get("load_source", ""),
        }
    )


@app.get("/api/dashboard")
def api_dashboard(
    min_original: float = Query(10_000.0, ge=0),
    department: str = Query("(all)"),
    procedure: str = Query("(all)"),
    selected_ref: str | None = Query(None),
):
    try:
        payload = build_dashboard_payload(min_original, department, procedure, selected_ref)
        return jsonable_encoder(payload)
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "reason": "server_error",
                "error": str(e),
                "ranked": [],
                "rows_loaded": 0,
            },
        )


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
