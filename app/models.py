"""ORM models: users, applications, documents, findings, verifications,
alerts, audit log, mock AICTE records, extraction results."""
from __future__ import annotations

import datetime as dt
import enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Role(str, enum.Enum):
    APPLICANT = "applicant"
    SCRUTINY_OFFICER = "scrutiny_officer"
    ADMIN = "admin"


class ApplicationStatus(str, enum.Enum):
    SUBMITTED = "Submitted"
    UNDER_SCRUTINY = "Under Scrutiny"
    DEFICIENCY_RECTIFIABLE = "Deficiency - Rectifiable"
    VERIFICATION_PENDING = "Verification Pending"
    RECOMMENDED = "Recommended"
    MANUAL_REVIEW = "Manual Review Required"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=Role.APPLICANT.value)
    institution_aicte_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="applicant")


# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    institution_name: Mapped[str] = mapped_column(String(255), default="")
    aicte_id: Mapped[str] = mapped_column(String(32), default="")
    programme: Mapped[str] = mapped_column(String(128), default="")
    intake: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(64), default=ApplicationStatus.SUBMITTED.value, index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    deficiency_count: Mapped[int] = mapped_column(Integer, default=0)
    form_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    applicant: Mapped[User] = relationship(back_populates="applications")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    verifications: Mapped[list["Verification"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    # classification & extraction
    doc_type: Mapped[str] = mapped_column(String(64), default="UNKNOWN", index=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # hashes for duplicate detection
    sha256: Mapped[str] = mapped_column(String(64), index=True, default="")
    phash: Mapped[str] = mapped_column(String(32), index=True, default="")

    # bookkeeping
    is_rectification: Mapped[bool] = mapped_column(Boolean, default=False)
    replaces_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="documents")


# --------------------------------------------------------------------------- #
# Findings (checklist misses, cross-check mismatches, anomalies)
# --------------------------------------------------------------------------- #
class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)  # checklist|anomaly|compliance
    type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default=Severity.LOW.value)
    message: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    field: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    disclaimer: Mapped[str] = mapped_column(
        String(255), default="Preliminary indicator – human verification required"
    )
    officer_action: Mapped[str] = mapped_column(String(32), default="PENDING")
    officer_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="findings")


# --------------------------------------------------------------------------- #
# Verification results from mock issuing authorities
# --------------------------------------------------------------------------- #
class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(32))  # nba|naac|fire|land
    reference: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default=VerificationStatus.VERIFICATION_PENDING.value)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped[Application] = relationship(back_populates="verifications")


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("applications.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32))  # missing|expiring|pending_verify|anomaly
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Optional[Application]] = relationship(back_populates="alerts")


# --------------------------------------------------------------------------- #
# Audit log (append-only hash chain)
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    row_hash: Mapped[str] = mapped_column(String(64), index=True)


# --------------------------------------------------------------------------- #
# Mock AICTE records (30 institutions) — populated in Stage 2
# --------------------------------------------------------------------------- #
class AicteRecord(Base):
    __tablename__ = "aicte_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aicte_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    programmes: Mapped[dict] = mapped_column(JSON, default=dict)  # {prog: intake}
    previous_eoa_valid_until: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ter_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    faculty_count: Mapped[int] = mapped_column(Integer, default=0)
    deficiency_status: Mapped[str] = mapped_column(String(64), default="None")
    state: Mapped[str] = mapped_column(String(64), default="")


# --------------------------------------------------------------------------- #
# Mock issuing-authority certificates — populated in Stage 2
# --------------------------------------------------------------------------- #
class IssuedCertificate(Base):
    __tablename__ = "issued_certificates"
    __table_args__ = (UniqueConstraint("source", "cert_number", name="uq_source_cert"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)  # nba|naac|fire|land
    cert_number: Mapped[str] = mapped_column(String(128), index=True)
    holder: Mapped[str] = mapped_column(String(255))
    issued_on: Mapped[str] = mapped_column(String(32))
    valid_until: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="VALID")
    extra: Mapped[dict] = mapped_column(JSON, default=dict)