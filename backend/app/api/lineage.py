from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.common import get_record
from app.core.security import DB, User, authorize
from app.lineage.service import graph, ingest_event, validate_edge
from app.models.entities import (
    DataAsset,
    DataField,
    LineageEdge,
)
from app.schemas.requests import (
    CustomerIngestion,
    EdgeInput,
    OpenLineageEvent,
)
from app.services.audit import audit, serialize

router = APIRouter(prefix="/api", tags=["lineage"])


@router.get("/lineage/assets/{id}")
def asset_lineage(id: int, db: DB, user: User):
    return graph(db, id)


@router.get("/lineage/upstream/{id}")
def upstream(id: int, db: DB, user: User):
    return graph(db, id, "upstream")


@router.get("/lineage/downstream/{id}")
def downstream(id: int, db: DB, user: User):
    return graph(db, id, "downstream")


@router.get("/lineage/fields/{id}")
def field_lineage(id: int, db: DB, user: User):
    field = get_record(db, DataField, id)
    return graph(db, field.data_asset_id, field_id=id)


@router.post("/lineage/edges", status_code=201)
def create_edge(data: EdgeInput, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    validate_edge(db, data)
    key = (
        f"field:{data.source_field_id}:{data.target_field_id}"
        if data.source_field_id
        else "dataset"
    )
    record = LineageEdge(**data.model_dump(), edge_key=key)
    db.add(record)
    audit(db, user, "Lineage documented", record)
    return serialize(record)


@router.delete("/lineage/edges/{id}")
def delete_edge(id: int, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    edge = get_record(db, LineageEdge, id)
    audit(db, user, "Lineage withdrawn", edge, serialize(edge))
    db.delete(edge)
    return {"removed": id}


@router.post("/lineage/events")
def lineage_event(data: OpenLineageEvent, db: DB, user: User):
    authorize(user, "GOVERNANCE_ANALYST")
    return ingest_event(db, data, user)


@router.post("/ingestion/customer-clean")
def ingest_clean_customers(data: "CustomerIngestion", db: DB, user: User):
    import os
    import tempfile
    from pathlib import Path

    import pandas as pd

    from app.core.config import get_settings

    authorize(user, "GOVERNANCE_ANALYST")
    asset = db.scalar(select(DataAsset).where(DataAsset.name == "customer_clean"))
    if not asset:
        raise HTTPException(409, "Seed the catalog first")
    path = get_settings().data_root / "curated/customer_clean.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents quality workers observing a partially written file.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
        pd.DataFrame([r.model_dump() for r in data.records]).to_csv(file, index=False)
        temporary = Path(file.name)
    os.replace(temporary, path)
    audit(db, user, f"Synthetic dataset ingested: {data.run_id}", asset)
    return {"asset_id": asset.id, "rows": len(data.records)}
