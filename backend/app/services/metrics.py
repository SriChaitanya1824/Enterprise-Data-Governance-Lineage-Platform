from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from app.governance.engine import as_utc
from app.models.entities import (
    BusinessDomain,
    DataAsset,
    DataField,
    GovernanceException,
    LineageEdge,
    QualityRule,
    now,
)
from app.quality.service import latest_results, quality_score


def adoption(db):
    rows = []
    edges = db.scalars(select(LineageEdge)).all()
    linked = {e.source_asset_id for e in edges} | {e.target_asset_id for e in edges}
    quality_assets = set(db.scalars(select(QualityRule.data_asset_id)))
    for domain in db.scalars(select(BusinessDomain).where(BusinessDomain.active.is_(True))):
        assets = db.scalars(
            select(DataAsset).where(
                DataAsset.business_domain_id == domain.id, DataAsset.status == "Active"
            )
        ).all()
        if not assets:
            continue
        total = len(assets)

        def pct(count):
            return round(100 * count / total, 1)

        metrics = {
            "ownership": pct(sum(a.owner_id is not None for a in assets)),
            "stewardship": pct(sum(a.steward_id is not None for a in assets)),
            "metadata": pct(
                sum(
                    bool(
                        a.description.strip()
                        and a.source_system.strip()
                        and a.physical_location.strip()
                    )
                    for a in assets
                )
            ),
            "classification": pct(
                sum(
                    a.classification in {"Public", "Internal", "Confidential", "Restricted"}
                    for a in assets
                )
            ),
            "lineage": pct(sum(a.id in linked for a in assets)),
            "quality": pct(sum(a.id in quality_assets for a in assets)),
            "review": pct(
                sum(
                    a.last_reviewed_at is not None
                    and now() - timedelta(days=90) <= as_utc(a.last_reviewed_at) <= now()
                    for a in assets
                )
            ),
        }
        ids = {a.id for a in assets}
        exceptions = db.scalars(
            select(GovernanceException).where(GovernanceException.status != "Closed")
        ).all()
        rows.append(
            {
                "domain_id": domain.id,
                "domain": domain.name,
                "assets": total,
                **metrics,
                "adoption_score": round(sum(metrics.values()) / len(metrics), 1),
                "open_exceptions": sum(e.data_asset_id in ids for e in exceptions),
            }
        )
    return rows


def dashboard(db):
    assets = db.scalars(select(DataAsset).where(DataAsset.status == "Active")).all()
    exceptions = db.scalars(select(GovernanceException)).all()
    open_exceptions = [e for e in exceptions if e.status != "Closed"]
    edges = db.scalars(select(LineageEdge)).all()
    linked = {e.source_asset_id for e in edges} | {e.target_asset_id for e in edges}
    scores = [s for a in assets if (s := quality_score(db, a.id)) is not None]
    adoption_rows = adoption(db)
    return {
        "total_assets": len(assets),
        "cdes": len(db.scalars(select(DataField).where(DataField.is_cde.is_(True))).all()),
        "governed_assets": sum(
            bool(a.owner_id and a.steward_id and a.description and a.classification) for a in assets
        ),
        "missing_ownership": sum(a.owner_id is None for a in assets),
        "missing_lineage": sum(a.id not in linked for a in assets),
        "open_exceptions": len(open_exceptions),
        "overdue_exceptions": sum(as_utc(e.due_date) < now() for e in open_exceptions),
        "average_quality": round(sum(scores) / len(scores), 2) if scores else None,
        "adoption_score": (
            round(sum(r["adoption_score"] * r["assets"] for r in adoption_rows) / len(assets), 1)
            if assets
            else 0
        ),
        "adoption": adoption_rows,
        "exception_status": dict(Counter(e.status for e in exceptions)),
        "exception_severity": dict(Counter(e.severity for e in open_exceptions)),
        "quality_results": dict(
            Counter("Passed" if r.passed else "Failed" for r in latest_results(db))
        ),
        "assets_by_domain": {r["domain"]: r["assets"] for r in adoption_rows},
        "lineage_completeness": {
            "Documented": sum(a.id in linked for a in assets),
            "Missing": sum(a.id not in linked for a in assets),
        },
        "quality_coverage": len(scores),
    }
