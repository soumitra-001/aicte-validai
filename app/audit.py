"""Append-only audit log with SHA-256 hash chaining.

Each row stores prev_hash (previous row's hash) and row_hash = SHA256(
  prev_hash | ts_iso | actor | action | entity | entity_id | canonical_json(details)
).
Genesis row has prev_hash = '0'*64. `verify_chain` walks all rows and re-derives
hashes; any mutation breaks the chain.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditLog, utcnow

GENESIS = "0" * 64


def _canonical(details: dict[str, Any] | None) -> str:
    return json.dumps(details or {}, sort_keys=True, separators=(",", ":"), default=str)


def _row_hash(
    prev_hash: str,
    ts: dt.datetime,
    actor: str,
    action: str,
    entity: str,
    entity_id: int | None,
    details: dict[str, Any] | None,
) -> str:
    material = "|".join(
        [
            prev_hash,
            ts.astimezone(dt.timezone.utc).isoformat(),
            actor,
            action,
            entity,
            str(entity_id if entity_id is not None else ""),
            _canonical(details),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append(
    db: Session,
    actor: str,
    action: str,
    entity: str = "",
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one audit row and commit. Returns the persisted row."""
    last = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev_hash = last.row_hash if last else GENESIS
    ts = utcnow()
    row = AuditLog(
        ts=ts,
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details or {},
        prev_hash=prev_hash,
    )
    row.row_hash = _row_hash(prev_hash, ts, actor, action, entity, entity_id, details)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def verify_chain(db: Session) -> dict[str, Any]:
    """Return {ok, rows, broken_at} after re-hashing the entire chain."""
    rows = db.execute(select(AuditLog).order_by(AuditLog.id.asc())).scalars().all()
    prev = GENESIS
    for i, row in enumerate(rows):
        expected = _row_hash(
            prev, row.ts, row.actor, row.action, row.entity, row.entity_id, row.details
        )
        if row.prev_hash != prev or row.row_hash != expected:
            return {"ok": False, "rows": len(rows), "broken_at": row.id, "index": i}
        prev = row.row_hash
    return {"ok": True, "rows": len(rows), "broken_at": None, "index": None}