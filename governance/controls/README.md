# Policy registry

The executable policy predicates and stable seed definitions live in `backend/app/governance/engine.py`. They are seeded into GovernanceControl records and exposed via authenticated APIs. The eight codes are OWNERSHIP, STEWARDSHIP, METADATA, CLASSIFICATION, CDE, LINEAGE, QUALITY and REVIEW.

This directory documents their governance ownership without introducing a second inconsistent policy implementation. Full predicate scopes and evidence requirements are in `docs/governance-controls.md`. SQLAlchemy persists each execution and exception. Declarative policy configuration/versioning is future work.
