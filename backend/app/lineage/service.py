from fastapi import HTTPException
from sqlalchemy import select

from app.models.entities import DataAsset, DataField, LineageEdge, LineageEvent
from app.services.audit import audit, serialize


def graph(db, asset_id, direction="both", field_id=None):
    if not db.get(DataAsset, asset_id):
        raise HTTPException(404, "Asset not found")
    edges = db.scalars(select(LineageEdge)).all()
    visited = {field_id if field_id is not None else asset_id}
    selected = {}
    # Separate directional traversals prevent following a sibling branch upstream then back down.
    for traversal in (["upstream", "downstream"] if direction == "both" else [direction]):
        frontier = set(visited)
        seen = set(visited)
        while frontier:
            next_frontier = set()
            for edge in edges:
                src = edge.source_field_id if field_id is not None else edge.source_asset_id
                dst = edge.target_field_id if field_id is not None else edge.target_asset_id
                if src is None or dst is None:
                    continue
                start, end = (dst, src) if traversal == "upstream" else (src, dst)
                if start in frontier:
                    selected[edge.id] = edge
                    if end not in seen:
                        next_frontier.add(end)
                        seen.add(end)
            frontier = next_frontier
    node_ids = {asset_id}
    for edge in selected.values():
        node_ids.update([edge.source_asset_id, edge.target_asset_id])
    return {
        "nodes": [serialize(db.get(DataAsset, i)) for i in sorted(node_ids)],
        "edges": [serialize(e) for e in selected.values()],
        "scope": "field" if field_id is not None else "dataset",
        "direction": direction,
    }


def validate_edge(db, data):
    if data.source_asset_id == data.target_asset_id:
        raise HTTPException(422, "Self lineage is not allowed")
    for asset_id in [data.source_asset_id, data.target_asset_id]:
        if not db.get(DataAsset, asset_id):
            raise HTTPException(422, "Unknown lineage asset")
    if (data.source_field_id is None) != (data.target_field_id is None):
        raise HTTPException(422, "Both source and target fields are required for field lineage")
    for fid, aid in [
        (data.source_field_id, data.source_asset_id),
        (data.target_field_id, data.target_asset_id),
    ]:
        if fid is not None:
            field = db.get(DataField, fid)
            if not field or field.data_asset_id != aid:
                raise HTTPException(422, "Lineage field must belong to its declared asset")
    downstream = graph(db, data.target_asset_id, "downstream")
    if any(n["id"] == data.source_asset_id for n in downstream["nodes"]):
        raise HTTPException(422, "Lineage must remain acyclic")


def ingest_event(db, event, user):
    run_id = event.run.get("runId")
    job_name = event.job.get("name")
    if (
        not isinstance(run_id, str)
        or not run_id
        or len(run_id) > 120
        or not isinstance(job_name, str)
        or not job_name
        or len(job_name) > 200
    ):
        raise HTTPException(422, "run.runId and job.name are required")
    existing = db.scalar(
        select(LineageEvent).where(
            LineageEvent.run_id == run_id,
            LineageEvent.job_name == job_name,
            LineageEvent.event_type == event.eventType,
        )
    )
    if existing:
        return {"event_id": existing.id, "duplicate": True, "edges_captured": 0}
    record = LineageEvent(
        run_id=run_id,
        event_type=event.eventType,
        job_name=job_name,
        payload=event.model_dump(mode="json"),
    )
    db.add(record)
    count = 0
    if event.eventType == "COMPLETE":
        from app.schemas.requests import EdgeInput

        for inp in event.inputs:
            for out in event.outputs:
                # Resolve by catalog name AND namespace to prevent accidental cross-system attribution.
                source = db.scalar(
                    select(DataAsset).where(
                        DataAsset.name == inp.name, DataAsset.source_system == inp.namespace
                    )
                )
                target = db.scalar(
                    select(DataAsset).where(
                        DataAsset.name == out.name, DataAsset.source_system == out.namespace
                    )
                )
                if not source or not target:
                    raise HTTPException(
                        422, "Register input/output datasets with matching namespace first"
                    )
                data = EdgeInput(
                    source_asset_id=source.id,
                    target_asset_id=target.id,
                    transformation=f"OpenLineage job {job_name}; dataset-level capture",
                )
                validate_edge(db, data)
                edge = db.scalar(
                    select(LineageEdge).where(
                        LineageEdge.source_asset_id == source.id,
                        LineageEdge.target_asset_id == target.id,
                        LineageEdge.edge_key == "dataset",
                    )
                )
                if edge:
                    before = serialize(edge)
                    edge.run_id = run_id
                    edge.origin = "OpenLineage"
                    edge.transformation = data.transformation
                    audit(db, user, "Lineage refreshed", edge, before)
                else:
                    edge = LineageEdge(
                        **data.model_dump(), edge_key="dataset", origin="OpenLineage", run_id=run_id
                    )
                    db.add(edge)
                    audit(db, user, "Lineage captured", edge)
                count += 1
    audit(db, user, "OpenLineage event received", record)
    return {"event_id": record.id, "duplicate": False, "edges_captured": count}
