import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("governance")
app = FastAPI(title="Enterprise Data Governance & Lineage Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)


@app.middleware("http")
async def request_log(request: Request, call_next):
    start = time.monotonic()
    request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, error):
    return JSONResponse(
        status_code=409, content={"detail": "Record conflicts with existing data or references"}
    )


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "service": "enterprise-governance"}
