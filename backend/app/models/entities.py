from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def now():
    return datetime.now(timezone.utc)


class Record(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class BusinessDomain(Record):
    __tablename__ = "business_domains"
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)


class Person(Record):
    __tablename__ = "people"
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(40))
    business_domain_id: Mapped[int | None] = mapped_column(ForeignKey("business_domains.id"))
    active: Mapped[bool] = mapped_column(default=True)
    password_hash: Mapped[str] = mapped_column(Text)


class DataAsset(Record):
    __tablename__ = "data_assets"
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    asset_type: Mapped[str] = mapped_column(String(40), default="Dataset")
    business_domain_id: Mapped[int] = mapped_column(ForeignKey("business_domains.id"), index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    steward_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    classification: Mapped[str] = mapped_column(String(30), index=True, default="Internal")
    criticality: Mapped[str] = mapped_column(String(20), default="Standard")
    regulatory_relevance: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(20), default="Active")
    source_system: Mapped[str] = mapped_column(String(120), default="")
    physical_location: Mapped[str] = mapped_column(String(240), default="")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BusinessTerm(Record):
    __tablename__ = "business_terms"
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    definition: Mapped[str] = mapped_column(Text)
    business_domain_id: Mapped[int] = mapped_column(ForeignKey("business_domains.id"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    steward_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    status: Mapped[str] = mapped_column(String(20), default="Active")
    approval_status: Mapped[str] = mapped_column(String(20), default="Draft")


class DataField(Record):
    __tablename__ = "data_fields"
    __table_args__ = (UniqueConstraint("data_asset_id", "name"),)
    data_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    data_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text, default="")
    nullable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_cde: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    classification: Mapped[str] = mapped_column(String(30), default="Internal")
    business_term_id: Mapped[int | None] = mapped_column(ForeignKey("business_terms.id"))
    regulatory_tag: Mapped[str | None] = mapped_column(String(100))


class LineageEdge(Record):
    __tablename__ = "lineage_edges"
    __table_args__ = (UniqueConstraint("source_asset_id", "target_asset_id", "edge_key"),)
    source_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    target_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    source_field_id: Mapped[int | None] = mapped_column(ForeignKey("data_fields.id"))
    target_field_id: Mapped[int | None] = mapped_column(ForeignKey("data_fields.id"))
    edge_key: Mapped[str] = mapped_column(String(120), default="dataset")
    transformation: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(30), default="Documented")
    run_id: Mapped[str | None] = mapped_column(String(120))


class LineageEvent(Record):
    __tablename__ = "lineage_events"
    __table_args__ = (UniqueConstraint("run_id", "event_type", "job_name"),)
    run_id: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(30))
    job_name: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)


class QualityRule(Record):
    __tablename__ = "quality_rules"
    __table_args__ = (UniqueConstraint("data_asset_id", "name"),)
    data_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    field_id: Mapped[int | None] = mapped_column(ForeignKey("data_fields.id"))
    name: Mapped[str] = mapped_column(String(160))
    expectation: Mapped[str] = mapped_column(String(120))
    parameters: Mapped[dict] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(20), default="High")


class QualityResult(Record):
    __tablename__ = "quality_results"
    __table_args__ = (UniqueConstraint("rule_id", "run_id"),)
    rule_id: Mapped[int] = mapped_column(ForeignKey("quality_rules.id"), index=True)
    data_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    run_id: Mapped[str] = mapped_column(String(120))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float)
    expected_value: Mapped[dict] = mapped_column(JSON)
    actual_result: Mapped[dict] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(20))
    execution_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GovernanceControl(Record):
    __tablename__ = "governance_controls"
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(default=True)


class ControlExecution(Record):
    __tablename__ = "control_executions"
    __table_args__ = (UniqueConstraint("control_id", "data_asset_id", "run_id"),)
    control_id: Mapped[int] = mapped_column(ForeignKey("governance_controls.id"))
    data_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    run_id: Mapped[str] = mapped_column(String(120))
    result: Mapped[str] = mapped_column(String(10))
    severity: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(Text, default="")
    execution_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GovernanceException(Record):
    __tablename__ = "governance_exceptions"
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("governance_controls.id"))
    data_asset_id: Mapped[int] = mapped_column(ForeignKey("data_assets.id"), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Open", index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    remediation_plan: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "uq_active_exception",
    GovernanceException.control_id,
    GovernanceException.data_asset_id,
    unique=True,
    postgresql_where=GovernanceException.status != "Closed",
    sqlite_where=GovernanceException.status != "Closed",
)


class Evidence(Record):
    __tablename__ = "evidence"
    exception_id: Mapped[int] = mapped_column(ForeignKey("governance_exceptions.id"), index=True)
    document_name: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(100))
    local_reference: Mapped[str] = mapped_column(String(240))
    submitted_by: Mapped[int] = mapped_column(ForeignKey("people.id"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Pending Review")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    review_notes: Mapped[str] = mapped_column(Text, default="")


class AuditEvent(Record):
    __tablename__ = "audit_events"
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    actor: Mapped[str] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[int] = mapped_column(Integer)
    before_value: Mapped[dict | None] = mapped_column(JSON)
    after_value: Mapped[dict | None] = mapped_column(JSON)


# Portable database constraints complement validated API enums.
Base.metadata.tables["people"].append_constraint(
    CheckConstraint(
        "role IN ('ADMIN','GOVERNANCE_ANALYST','DATA_OWNER','DATA_STEWARD','REVIEWER')",
        name="ck_person_role",
    )
)
Base.metadata.tables["data_assets"].append_constraint(
    CheckConstraint(
        "classification IN ('Public','Internal','Confidential','Restricted')",
        name="ck_asset_classification",
    )
)
Base.metadata.tables["data_assets"].append_constraint(
    CheckConstraint("criticality IN ('Standard','Critical')", name="ck_asset_criticality")
)
Base.metadata.tables["data_assets"].append_constraint(
    CheckConstraint("status IN ('Active','Retired')", name="ck_asset_status")
)
Base.metadata.tables["data_fields"].append_constraint(
    CheckConstraint(
        "classification IN ('Public','Internal','Confidential','Restricted')",
        name="ck_field_classification",
    )
)
Base.metadata.tables["governance_exceptions"].append_constraint(
    CheckConstraint(
        "status IN ('Open','Assigned','Remediation in Progress','Pending Review','Closed','Rejected')",
        name="ck_exception_status",
    )
)
Base.metadata.tables["governance_exceptions"].append_constraint(
    CheckConstraint("severity IN ('Low','Medium','High','Critical')", name="ck_exception_severity")
)
Base.metadata.tables["quality_results"].append_constraint(
    CheckConstraint("score >= 0 AND score <= 100", name="ck_quality_score")
)
Base.metadata.tables["control_executions"].append_constraint(
    CheckConstraint("result IN ('PASS','FAIL','SKIP')", name="ck_control_result")
)
Base.metadata.tables["evidence"].append_constraint(
    CheckConstraint("status IN ('Pending Review','Approved','Rejected')", name="ck_evidence_status")
)
