from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from app.api.common import Page, Size, enrich_asset, get_record, page_records
from app.core.security import DB, User, authorize
from app.governance.engine import execute_controls
from app.models.entities import (
    AuditEvent,
    ControlExecution,
    DataAsset,
    Evidence,
    GovernanceControl,
    GovernanceException,
    QualityRule,
)
from app.quality.service import execute_quality, latest_results
from app.schemas.requests import (
    EvidenceInput,
    EvidenceReview,
    ExceptionTransition,
    RunInput,
)
from app.schemas.responses import PageResponse, RecordResponse
from app.services.audit import audit, serialize
from app.services.workflow import transition_exception

router = APIRouter(prefix="/api", tags=["governance"])


@router.get("/data-quality/rules", response_model=PageResponse[RecordResponse])
def quality_rules(db: DB, user: User, page: Page = 1, page_size: Size = 100):
    return page_records(db, select(QualityRule).order_by(QualityRule.id), page, page_size)


@router.get("/data-quality/results")
def quality_results(db: DB, user: User, asset_id: int | None = None):
    return {"items": [serialize(r) for r in latest_results(db, asset_id)]}


@router.post("/data-quality/run")
def run_quality(data: RunInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    return execute_quality(db, user, data.run_id)


@router.get("/governance-controls", response_model=PageResponse[RecordResponse])
def controls(db: DB, user: User, page: Page = 1, page_size: Size = 100):
    return page_records(
        db, select(GovernanceControl).order_by(GovernanceControl.id), page, page_size
    )


@router.post("/governance-controls/run")
def run_controls(data: RunInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    return execute_controls(db, user, data.run_id)


@router.get("/control-executions", response_model=PageResponse[RecordResponse])
def executions(
    db: DB, user: User, asset_id: int | None = None, page: Page = 1, page_size: Size = 20
):
    query = select(ControlExecution).order_by(ControlExecution.id.desc())
    if asset_id:
        query = query.where(ControlExecution.data_asset_id == asset_id)
    return page_records(db, query, page, page_size)


@router.get("/exceptions", response_model=PageResponse[RecordResponse])
def exceptions(
    db: DB,
    user: User,
    status: str | None = None,
    severity: str | None = None,
    domain_id: int | None = None,
    q: str = "",
    page: Page = 1,
    page_size: Size = 20,
):
    query = (
        select(GovernanceException)
        .join(DataAsset, DataAsset.id == GovernanceException.data_asset_id)
        .order_by(GovernanceException.id.desc())
    )
    if status:
        query = query.where(GovernanceException.status == status)
    if severity:
        query = query.where(GovernanceException.severity == severity)
    if domain_id:
        query = query.where(DataAsset.business_domain_id == domain_id)
    if q:
        query = query.where(
            or_(GovernanceException.reference.ilike(f"%{q}%"), DataAsset.name.ilike(f"%{q}%"))
        )
    result = page_records(db, query, page, page_size)
    for item in result["items"]:
        item["asset_name"] = get_record(db, DataAsset, item["data_asset_id"]).name
        item["control_name"] = get_record(db, GovernanceControl, item["control_id"]).name
    return result


@router.get("/exceptions/{id}")
def exception_detail(id: int, db: DB, user: User):
    record = get_record(db, GovernanceException, id)
    result = serialize(record)
    result["asset"] = enrich_asset(db, db.get(DataAsset, record.data_asset_id))
    result["control"] = serialize(db.get(GovernanceControl, record.control_id))
    result["evidence"] = [
        serialize(e) for e in db.scalars(select(Evidence).where(Evidence.exception_id == id))
    ]
    result["history"] = [
        serialize(a)
        for a in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_type == "governance_exceptions", AuditEvent.entity_id == id)
            .order_by(AuditEvent.id)
        )
    ]
    return result


@router.post("/exceptions/{id}/transition")
def exception_transition(id: int, data: ExceptionTransition, db: DB, user: User):
    record = get_record(db, GovernanceException, id)
    return transition_exception(db, record, data, user)


@router.get("/evidence", response_model=PageResponse[RecordResponse])
def evidence(db: DB, user: User, page: Page = 1, page_size: Size = 20):
    return page_records(db, select(Evidence).order_by(Evidence.id.desc()), page, page_size)


@router.post("/evidence", status_code=201)
def submit_evidence(data: EvidenceInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST", "DATA_OWNER", "DATA_STEWARD")
    exception = get_record(db, GovernanceException, data.exception_id)
    if exception.status != "Remediation in Progress":
        raise HTTPException(409, "Evidence can be submitted during remediation")
    if user.role in {"DATA_OWNER", "DATA_STEWARD"} and exception.assignee_id != user.id:
        raise HTTPException(403, "Evidence must be submitted by the assigned remediator")
    record = Evidence(**data.model_dump(), submitted_by=user.id)
    db.add(record)
    audit(db, user, "Evidence submitted", record)
    return serialize(record)


@router.post("/evidence/{id}/review")
def review_evidence(id: int, data: EvidenceReview, db: DB, user: User):
    authorize(user, "REVIEWER")
    record = get_record(db, Evidence, id)
    exception = get_record(db, GovernanceException, record.exception_id)
    if exception.status != "Pending Review" or record.status != "Pending Review":
        raise HTTPException(409, "Evidence must be pending in an exception under review")
    if record.submitted_by == user.id or exception.assignee_id == user.id:
        raise HTTPException(403, "Evidence requires an independent reviewer")
    before = serialize(record)
    record.status = data.status
    record.reviewed_by = user.id
    record.review_notes = data.notes
    audit(db, user, "Evidence reviewed", record, before)
    return serialize(record)
