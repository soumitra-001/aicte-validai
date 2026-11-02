"""FastAPI entrypoint. Stage 1 bootstraps DB + auth stub; Stage 5 extends it."""
from __future__ import annotations

from fastapi import FastAPI

from .db import Base, engine
from . import models  # noqa: F401  (register models)

app = FastAPI(title="AICTE-ValidAI", version="0.1.0")

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "stage": "1"}
