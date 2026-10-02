from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.common import Page, Size, page_records
from app.core.security import DB, User
from app.models.entities import (
    AuditEvent,
    BusinessDomain,
    BusinessTerm,
    DataAsset,
    DataField,
    GovernanceException,
    Person,
)
from app.schemas.responses import PageResponse, RecordResponse
from app.services.metrics import adoption, dashboard

router = APIRouter(prefix="/api", tags=["reporting"])


@router.get("/adoption")
def adoption_metrics(db: DB, user: User):
    return {"items": adoption(db)}


@router.get("/dashboard")
def dashboard_metrics(db: DB, user: User):
    return dashboard(db)


@router.get("/audit", response_model=PageResponse[RecordResponse])
def audit_log(
    db: DB, user: User, entity_type: str | None = None, page: Page = 1, page_size: Size = 20
):
    query = select(AuditEvent).order_by(AuditEvent.id.desc())
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    return page_records(db, query, page, page_size)


@router.get("/search")
def search(
    db: DB,
    user: User,
    q: Annotated[str, Query(min_length=2, max_length=160)],
    domain_id: int | None = None,
):
    results = []
    models = [
        (DataAsset, "assets", "name"),
        (DataField, "cdes", "name"),
        (BusinessTerm, "business-terms", "name"),
        (Person, "users", "name"),
        (BusinessDomain, "domains", "name"),
        (GovernanceException, "exceptions", "reference"),
    ]
    for model, kind, field in models:
        query = select(model).where(getattr(model, field).ilike(f"%{q}%"))
        if model == DataField:
            query = query.where(DataField.is_cde.is_(True))
        if domain_id:
            if hasattr(model, "business_domain_id"):
                query = query.where(model.business_domain_id == domain_id)
            elif model in {DataField, GovernanceException}:
                query = query.join(
                    DataAsset, getattr(model, "data_asset_id") == DataAsset.id
                ).where(DataAsset.business_domain_id == domain_id)
        for record in db.scalars(query.limit(20)):
            results.append({"id": record.id, "type": kind, "name": getattr(record, field)})
    return {"items": results}
