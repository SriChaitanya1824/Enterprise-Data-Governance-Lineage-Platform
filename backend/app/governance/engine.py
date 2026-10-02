from datetime import timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.lineage.service import graph
from app.models.entities import (
    BusinessTerm,
    ControlExecution,
    DataAsset,
    DataField,
    GovernanceControl,
    GovernanceException,
    LineageEdge,
    now,
)
from app.quality.service import quality_score
from app.services.audit import audit

CONTROL_DEFINITIONS = [
    (
        "OWNERSHIP",
        "Critical assets have accountable owners",
        "An active critical asset must have a data owner.",
        "High",
    ),
    (
        "STEWARDSHIP",
        "Critical assets have data stewards",
        "An active critical asset must have a data steward.",
        "High",
    ),
    (
        "METADATA",
        "Required metadata is documented",
        "Description, source system and physical location must be documented.",
        "Medium",
    ),
    (
        "CLASSIFICATION",
        "Classification is consistent",
        "Field sensitivity cannot exceed the containing asset's classification.",
        "High",
    ),
    (
        "CDE",
        "Critical data elements have governance profiles",
        "CDEs need ownership, stewardship, definitions and approved business terms.",
        "Critical",
    ),
    (
        "LINEAGE",
        "Regulatory data is traceable to source",
        "A regulatory output needs a path to a documented non-report source; regulatory CDEs need documented field lineage.",
        "High",
    ),
    (
        "QUALITY",
        "Critical assets meet quality threshold",
        "Latest observed row-level quality must be at least 95%.",
        "High",
    ),
    (
        "REVIEW",
        "Asset reviews are current",
        "Active governed assets must have a review within 90 days.",
        "Medium",
    ),
]
LEVELS = {"Public": 0, "Internal": 1, "Confidential": 2, "Restricted": 3}


def as_utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def evaluate(db, control, asset):
    fields = db.scalars(select(DataField).where(DataField.data_asset_id == asset.id)).all()
    cdes = [f for f in fields if f.is_cde]
    critical = asset.criticality == "Critical" or bool(cdes)
    code = control.code
    detail = {"asset": asset.name, "policy": control.description}
    applicable = True
    if code == "OWNERSHIP":
        applicable = critical
        passed = asset.owner_id is not None
        detail["owner_id"] = asset.owner_id
    elif code == "STEWARDSHIP":
        applicable = critical
        passed = asset.steward_id is not None
        detail["steward_id"] = asset.steward_id
    elif code == "METADATA":
        missing = [
            k
            for k in ["description", "source_system", "physical_location"]
            if not getattr(asset, k).strip()
        ]
        passed = not missing
        detail["missing"] = missing
    elif code == "CLASSIFICATION":
        invalid = [
            f.name
            for f in fields
            if LEVELS.get(f.classification, 99) > LEVELS.get(asset.classification, -1)
        ]
        passed = asset.classification in LEVELS and not invalid
        detail["inconsistent_fields"] = invalid
    elif code == "CDE":
        applicable = bool(cdes)
        gaps = []
        for field in cdes:
            term = db.get(BusinessTerm, field.business_term_id) if field.business_term_id else None
            if not (
                asset.owner_id
                and asset.steward_id
                and field.description.strip()
                and field.classification in LEVELS
                and term
                and term.approval_status == "Approved"
            ):
                gaps.append(field.name)
        passed = not gaps
        detail["incomplete_cdes"] = gaps
    elif code == "LINEAGE":
        applicable = asset.regulatory_relevance
        edges = db.scalars(select(LineageEdge).where(LineageEdge.target_asset_id == asset.id)).all()
        traced = graph(db, asset.id, "upstream")
        source_nodes = [
            n for n in traced["nodes"] if n["id"] != asset.id and n["asset_type"] != "Report"
        ]
        missing_fields = []
        for field in cdes:
            field_graph = graph(db, asset.id, "both", field.id)
            if not field_graph["edges"]:
                missing_fields.append(field.name)
        passed = bool(edges) and bool(source_nodes) and not missing_fields
        detail.update(upstream_assets=len(source_nodes), missing_field_lineage=missing_fields)
    elif code == "QUALITY":
        applicable = critical
        score = quality_score(db, asset.id)
        passed = score is not None and score >= 95
        detail.update(
            score=score, minimum=95, basis="Mean row success rate of latest result per quality rule"
        )
    elif code == "REVIEW":
        reviewed = as_utc(asset.last_reviewed_at) if asset.last_reviewed_at else None
        passed = reviewed is not None and now() - timedelta(days=90) <= reviewed <= now()
        detail["last_reviewed_at"] = reviewed.isoformat() if reviewed else None
    else:
        raise ValueError(f"Unknown control: {code}")
    return ("PASS" if passed else "FAIL") if applicable else "SKIP", detail


def execute_controls(db, user=None, run_id=None):
    run_id = run_id or str(uuid4())
    existing = db.scalars(select(ControlExecution).where(ControlExecution.run_id == run_id)).all()
    if existing:
        return {
            "run_id": run_id,
            "executions": len(existing),
            "failures": sum(e.result == "FAIL" for e in existing),
            "duplicate": True,
        }
    # Row locks serialize control executions on PostgreSQL and protect exception deduplication.
    assets = db.scalars(
        select(DataAsset)
        .where(DataAsset.status == "Active")
        .order_by(DataAsset.id)
        .with_for_update()
    ).all()
    controls = db.scalars(select(GovernanceControl).where(GovernanceControl.active.is_(True))).all()
    failures = 0
    for asset in assets:
        for control in controls:
            result, evidence = evaluate(db, control, asset)
            record = ControlExecution(
                control_id=control.id,
                data_asset_id=asset.id,
                run_id=run_id,
                result=result,
                severity=control.severity,
                evidence=evidence,
            )
            db.add(record)
            audit(db, user, "Governance control executed", record)
            if result == "FAIL":
                failures += 1
                active = db.scalar(
                    select(GovernanceException).where(
                        GovernanceException.control_id == control.id,
                        GovernanceException.data_asset_id == asset.id,
                        GovernanceException.status != "Closed",
                    )
                )
                if not active:
                    exception = GovernanceException(
                        reference=f"DG-{now().year}-{uuid4().hex[:10].upper()}",
                        control_id=control.id,
                        data_asset_id=asset.id,
                        severity=control.severity,
                        due_date=now() + timedelta(days=14),
                    )
                    db.add(exception)
                    audit(db, user, "Exception detected", exception)
    return {
        "run_id": run_id,
        "executions": len(assets) * len(controls),
        "failures": failures,
        "duplicate": False,
    }
