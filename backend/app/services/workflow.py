from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import authorize
from app.governance.engine import evaluate
from app.models.entities import DataAsset, Evidence, GovernanceControl, Person, now
from app.services.audit import audit, serialize

TRANSITIONS = {
    "Open": {"Assigned"},
    "Assigned": {"Remediation in Progress"},
    "Remediation in Progress": {"Pending Review"},
    "Pending Review": {"Closed", "Rejected"},
    "Rejected": {"Remediation in Progress"},
    "Closed": set(),
}


def transition_exception(db, exception, request, actor):
    if request.status not in TRANSITIONS[exception.status]:
        raise HTTPException(409, f"Cannot transition {exception.status} to {request.status}")
    if request.status in {"Closed", "Rejected"}:
        authorize(actor, "REVIEWER")
        if exception.assignee_id == actor.id:
            raise HTTPException(403, "A reviewer cannot close their own remediation")
    else:
        authorize(actor, "GOVERNANCE_ANALYST", "DATA_OWNER", "DATA_STEWARD")
        if actor.role in {"DATA_OWNER", "DATA_STEWARD"} and exception.assignee_id != actor.id:
            raise HTTPException(403, "Only the assigned remediator can progress this exception")
    before = serialize(exception)
    if request.status == "Assigned":
        assignee = db.get(Person, request.assignee_id) if request.assignee_id else None
        if not assignee or not assignee.active:
            raise HTTPException(422, "An active assignee is required")
        exception.assignee_id = assignee.id
    if request.status == "Remediation in Progress":
        if len(request.remediation_plan.strip()) < 10:
            raise HTTPException(422, "A meaningful remediation plan is required")
        exception.remediation_plan = request.remediation_plan
    evidence = db.scalars(select(Evidence).where(Evidence.exception_id == exception.id)).all()
    if request.status == "Pending Review" and not any(
        e.status == "Pending Review" for e in evidence
    ):
        raise HTTPException(409, "Submit new evidence before requesting review")
    if request.status == "Closed":
        if not any(e.status == "Approved" for e in evidence):
            raise HTTPException(409, "Approved evidence is required")
        control = db.get(GovernanceControl, exception.control_id)
        result, _ = evaluate(db, control, db.get(DataAsset, exception.data_asset_id))
        if result != "PASS":
            raise HTTPException(409, "The originating control must pass before closure")
        exception.closed_at = now()
    exception.status = request.status
    audit(db, actor, "Exception transitioned", exception, before)
    return serialize(exception)
