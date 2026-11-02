"""Pydantic request/response schemas shared across API and services."""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    full_name: str = ""
    institution_aicte_id: Optional[str] = None


class ApplicationCreate(BaseModel):
    category: str
    institution_name: str
    aicte_id: str
    programme: str = ""
    intake: Optional[int] = None
    form_payload: dict[str, Any] = Field(default_factory=dict)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    applicant_id: int
    category: str
    institution_name: str
    aicte_id: str
    programme: str
    intake: Optional[int]
    status: str
    risk_score: float
    deficiency_count: int
    created_at: dt.datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: str
    category: str
    type: str
    severity: str
    message: str
    evidence: dict[str, Any] = {}
    page: Optional[int] = None
    field: Optional[str] = None
    disclaimer: str
    officer_action: str
    officer_note: str


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    reference: str
    status: str
    detail: dict[str, Any] = {}
    attempts: int
    started_at: dt.datetime
    finished_at: Optional[dt.datetime] = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    application_id: Optional[int]
    kind: str
    message: str
    is_read: bool
    created_at: dt.datetime


class OfficerAction(BaseModel):
    action: str  # accept | dismiss | request_docs | send_inspection | mark_verified
    reason: str = ""