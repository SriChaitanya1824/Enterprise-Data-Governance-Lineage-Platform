from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from app.api.common import Page, Size, enrich_asset, get_record, page_records, validate_references
from app.core.security import DB, User, authorize
from app.governance.engine import LEVELS
from app.lineage.service import graph
from app.models.entities import (
    BusinessTerm,
    ControlExecution,
    DataAsset,
    DataField,
    GovernanceException,
    QualityRule,
)
from app.quality.service import latest_results
from app.schemas.requests import (
    AssetInput,
    AssetPatch,
    FieldInput,
    TermInput,
)
from app.schemas.responses import AssetResponse, PageResponse, RecordResponse
from app.services.audit import audit, serialize

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/assets", response_model=PageResponse[AssetResponse])
def assets(
    db: DB,
    user: User,
    page: Page = 1,
    page_size: Size = 20,
    q: str = "",
    domain_id: int | None = None,
    classification: str | None = None,
    criticality: str | None = None,
):
    query = select(DataAsset).order_by(DataAsset.name)
    if q:
        query = query.where(
            or_(DataAsset.name.ilike(f"%{q}%"), DataAsset.description.ilike(f"%{q}%"))
        )
    if domain_id:
        query = query.where(DataAsset.business_domain_id == domain_id)
    if classification:
        query = query.where(DataAsset.classification == classification)
    if criticality:
        query = query.where(DataAsset.criticality == criticality)
    response = page_records(db, query, page, page_size)
    response["items"] = [enrich_asset(db, db.get(DataAsset, r["id"])) for r in response["items"]]
    return response


@router.post("/assets", status_code=201)
def create_asset(data: AssetInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    validate_references(db, data)
    asset = DataAsset(**data.model_dump())
    db.add(asset)
    audit(db, user, "Asset registered", asset)
    return enrich_asset(db, asset)


@router.get("/assets/{id}", response_model=AssetResponse)
def asset_detail(id: int, db: DB, user: User):
    asset = get_record(db, DataAsset, id)
    record = enrich_asset(db, asset)
    record["fields"] = [
        serialize(f) for f in db.scalars(select(DataField).where(DataField.data_asset_id == id))
    ]
    record["quality_results"] = [serialize(r) for r in latest_results(db, id)]
    all_controls = db.scalars(
        select(ControlExecution)
        .where(ControlExecution.data_asset_id == id)
        .order_by(ControlExecution.id.desc())
    )
    latest: dict[int, dict] = {}
    for c in all_controls:
        latest.setdefault(c.control_id, serialize(c))
    record["controls"] = list(latest.values())
    record["exceptions"] = [
        serialize(e)
        for e in db.scalars(
            select(GovernanceException).where(GovernanceException.data_asset_id == id)
        )
    ]
    record["lineage"] = graph(db, id)
    return record


@router.patch("/assets/{id}")
def update_asset(id: int, data: AssetPatch, db: DB, user: User):
    asset = get_record(db, DataAsset, id)
    authorize(user, "GOVERNANCE_ANALYST", "DATA_OWNER", "DATA_STEWARD")
    changes = data.model_dump(exclude_unset=True)
    if user.role in {"DATA_OWNER", "DATA_STEWARD"}:
        assigned_id = asset.owner_id if user.role == "DATA_OWNER" else asset.steward_id
        allowed = {"description", "last_reviewed_at"}
        if assigned_id != user.id or not set(changes) <= allowed:
            raise HTTPException(
                403,
                "Owners and stewards may update description and review date for their assigned assets",
            )
    if any(
        v is None and k not in {"owner_id", "steward_id", "last_reviewed_at"}
        for k, v in changes.items()
    ):
        raise HTTPException(422, "Required metadata cannot be null")
    validate_references(db, data)
    if "classification" in changes:
        fields = db.scalars(select(DataField).where(DataField.data_asset_id == id)).all()
        if any(LEVELS[f.classification] > LEVELS[changes["classification"]] for f in fields):
            raise HTTPException(422, "Asset classification cannot be lower than its fields")
    before = serialize(asset)
    for key, value in changes.items():
        setattr(asset, key, value)
    audit(db, user, "Asset updated", asset, before)
    return enrich_asset(db, asset)


@router.delete("/assets/{id}")
def retire_asset(id: int, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    asset = get_record(db, DataAsset, id)
    before = serialize(asset)
    asset.status = "Retired"
    audit(db, user, "Asset retired", asset, before)
    return serialize(asset)


@router.get("/fields", response_model=PageResponse[RecordResponse])
def fields(db: DB, user: User, asset_id: int | None = None, page: Page = 1, page_size: Size = 20):
    query = select(DataField).order_by(DataField.id)
    if asset_id:
        query = query.where(DataField.data_asset_id == asset_id)
    return page_records(db, query, page, page_size)


def validate_field(db, data):
    asset = get_record(db, DataAsset, data.data_asset_id)
    if LEVELS[data.classification] > LEVELS[asset.classification]:
        raise HTTPException(422, "Field classification cannot exceed asset classification")
    if data.business_term_id:
        get_record(db, BusinessTerm, data.business_term_id)


@router.post("/fields", status_code=201)
def create_field(data: FieldInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    validate_field(db, data)
    field = DataField(**data.model_dump())
    db.add(field)
    audit(db, user, "Field registered", field)
    return serialize(field)


@router.put("/fields/{id}")
def update_field(id: int, data: FieldInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    field = get_record(db, DataField, id)
    if data.data_asset_id != field.data_asset_id:
        raise HTTPException(422, "Moving a field between assets would invalidate lineage")
    validate_field(db, data)
    before = serialize(field)
    for key, value in data.model_dump().items():
        setattr(field, key, value)
    audit(db, user, "Field updated", field, before)
    return serialize(field)


@router.get("/cdes", response_model=PageResponse[RecordResponse])
def cdes(
    db: DB,
    user: User,
    q: str = "",
    domain_id: int | None = None,
    page: Page = 1,
    page_size: Size = 20,
):
    query = (
        select(DataField)
        .join(DataAsset, DataAsset.id == DataField.data_asset_id)
        .where(DataField.is_cde.is_(True))
    )
    if q:
        query = query.where(
            or_(DataField.name.ilike(f"%{q}%"), DataField.description.ilike(f"%{q}%"))
        )
    if domain_id:
        query = query.where(DataAsset.business_domain_id == domain_id)
    response = page_records(db, query.order_by(DataField.id), page, page_size)
    for item in response["items"]:
        item["asset"] = enrich_asset(db, db.get(DataAsset, item["data_asset_id"]))
        term = db.get(BusinessTerm, item["business_term_id"]) if item["business_term_id"] else None
        item["term"] = term.name if term else None
    return response


@router.get("/cdes/{id}")
def cde_detail(id: int, db: DB, user: User):
    field = get_record(db, DataField, id)
    if not field.is_cde:
        raise HTTPException(404, "Field is not a CDE")
    record = serialize(field)
    record["asset"] = asset_detail(field.data_asset_id, db, user)
    term = db.get(BusinessTerm, field.business_term_id) if field.business_term_id else None
    record["business_term"] = serialize(term) if term else None
    record["lineage"] = graph(db, field.data_asset_id, field_id=id)
    record["quality_rules"] = [
        serialize(r) for r in db.scalars(select(QualityRule).where(QualityRule.field_id == id))
    ]
    return record


@router.get("/business-terms", response_model=PageResponse[RecordResponse])
def terms(
    db: DB,
    user: User,
    q: str = "",
    domain_id: int | None = None,
    page: Page = 1,
    page_size: Size = 20,
):
    query = select(BusinessTerm).order_by(BusinessTerm.name)
    if q:
        query = query.where(
            or_(BusinessTerm.name.ilike(f"%{q}%"), BusinessTerm.definition.ilike(f"%{q}%"))
        )
    if domain_id:
        query = query.where(BusinessTerm.business_domain_id == domain_id)
    return page_records(db, query, page, page_size)


@router.post("/business-terms", status_code=201)
def create_term(data: TermInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    validate_references(db, data)
    term = BusinessTerm(**data.model_dump())
    db.add(term)
    audit(db, user, "Business term created", term)
    return serialize(term)


@router.get("/business-terms/{id}")
def term_detail(id: int, db: DB, user: User):
    term = get_record(db, BusinessTerm, id)
    record = serialize(term)
    fields = db.scalars(select(DataField).where(DataField.business_term_id == id)).all()
    record["fields"] = [serialize(f) for f in fields]
    record["assets"] = [
        enrich_asset(db, db.get(DataAsset, i)) for i in sorted({f.data_asset_id for f in fields})
    ]
    return record


@router.put("/business-terms/{id}")
def update_term(id: int, data: TermInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    validate_references(db, data)
    term = get_record(db, BusinessTerm, id)
    before = serialize(term)
    for key, value in data.model_dump().items():
        setattr(term, key, value)
    term.approval_status = "Draft"
    audit(db, user, "Business term edited; approval reset", term, before)
    return serialize(term)


@router.post("/business-terms/{id}/approve")
def approve_term(id: int, db: DB, user: User):
    authorize(user, "REVIEWER")
    term = get_record(db, BusinessTerm, id)
    if not term.owner_id or not term.steward_id:
        raise HTTPException(409, "Assign an owner and steward before approval")
    before = serialize(term)
    term.approval_status = "Approved"
    audit(db, user, "Business term approved", term, before)
    return serialize(term)
