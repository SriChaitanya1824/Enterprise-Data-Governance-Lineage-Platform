from typing import Annotated

from fastapi import HTTPException, Query
from sqlalchemy import func, select

from app.models.entities import (
    BusinessDomain,
    Person,
)
from app.quality.service import quality_score
from app.services.audit import serialize

Page = Annotated[int, Query(ge=1)]


Size = Annotated[int, Query(ge=1, le=100)]


def get_record(db, model, id):
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


def page_records(db, query, page, page_size):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [serialize(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def validate_references(db, data):
    if hasattr(data, "business_domain_id"):
        get_record(db, BusinessDomain, data.business_domain_id)
    for key in ["owner_id", "steward_id"]:
        person_id = getattr(data, key, None)
        if person_id:
            person = get_record(db, Person, person_id)
            if not person.active:
                raise HTTPException(422, "Inactive governance stakeholder")


def enrich_asset(db, asset):
    record = serialize(asset)
    domain = db.get(BusinessDomain, asset.business_domain_id)
    record["domain"] = domain.name if domain else None
    for key in ["owner", "steward"]:
        person = (
            db.get(Person, getattr(asset, key + "_id")) if getattr(asset, key + "_id") else None
        )
        record[key] = person.name if person else None
    record["quality_score"] = quality_score(db, asset.id)
    return record
