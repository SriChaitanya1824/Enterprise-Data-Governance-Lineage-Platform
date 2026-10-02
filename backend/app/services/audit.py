from datetime import datetime

from sqlalchemy import inspect

from app.models.entities import AuditEvent


def serialize(record):
    return {
        attr.key: (
            value.isoformat() if isinstance(value := getattr(record, attr.key), datetime) else value
        )
        for attr in inspect(record).mapper.column_attrs
        if attr.key != "password_hash"
    }


def audit(db, actor, action, entity, before=None):
    db.flush()
    db.add(
        AuditEvent(
            actor_id=actor.id if actor else None,
            actor=actor.name if actor else "System",
            action=action,
            entity_type=entity.__tablename__,
            entity_id=entity.id,
            before_value=before,
            after_value=serialize(entity),
        )
    )
