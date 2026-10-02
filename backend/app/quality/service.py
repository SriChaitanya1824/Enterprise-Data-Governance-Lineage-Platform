import json
import math
from uuid import uuid4

import great_expectations as gx
import pandas as pd
from sqlalchemy import select

from app.core.config import get_settings
from app.models.entities import DataAsset, QualityResult, QualityRule
from app.services.audit import audit


def latest_results(db, asset_id=None):
    query = select(QualityResult).order_by(
        QualityResult.execution_time.desc(), QualityResult.id.desc()
    )
    if asset_id is not None:
        query = query.where(QualityResult.data_asset_id == asset_id)
    latest: dict[int, QualityResult] = {}
    for row in db.scalars(query):
        latest.setdefault(row.rule_id, row)
    return list(latest.values())


def quality_score(db, asset_id):
    results = latest_results(db, asset_id)
    return round(sum(r.score for r in results) / len(results), 2) if results else None


def execute_quality(db, user=None, run_id=None):
    run_id = run_id or str(uuid4())
    existing = db.scalars(select(QualityResult).where(QualityResult.run_id == run_id)).all()
    if existing:
        return {"run_id": run_id, "rules_evaluated": len(existing), "duplicate": True}
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas("synthetic_financial_data")
    rules = db.scalars(select(QualityRule)).all()
    batches = {}
    for rule in rules:
        if rule.data_asset_id not in batches:
            asset = db.get(DataAsset, rule.data_asset_id)
            root = get_settings().data_root.resolve()
            path = (root / asset.physical_location).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f"Quality input is not an accessible catalog file: {asset.name}")
            frame = pd.read_csv(path)
            data_asset = source.add_dataframe_asset(name=asset.name)
            definition = data_asset.add_batch_definition_whole_dataframe("whole_file")
            batches[asset.id] = definition.get_batch(batch_parameters={"dataframe": frame})
        expectation_class = getattr(gx.expectations, rule.expectation)
        validation = batches[rule.data_asset_id].validate(expectation_class(**rule.parameters))
        actual = sanitize(json.loads(json.dumps(validation.result, default=str)))
        unexpected = actual.get("unexpected_percent", 0 if validation.success else 100)
        result = QualityResult(
            rule_id=rule.id,
            data_asset_id=rule.data_asset_id,
            run_id=run_id,
            passed=bool(validation.success),
            score=round(100 - unexpected, 2),
            expected_value=rule.parameters,
            actual_result=actual,
            severity=rule.severity,
        )
        db.add(result)
        audit(db, user, "Quality rule evaluated", result)
    return {"run_id": run_id, "rules_evaluated": len(rules), "duplicate": False}


def sanitize(value):
    """GX may include NaN sample values; persist standards-compliant JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value
