"""Enforce portable governance values and quality bounds."""

from alembic import op

revision = "9bd07a1b03c1"
down_revision = "568969e8439a"
branch_labels = None
depends_on = None

CONSTRAINTS = [
    (
        "people",
        "ck_person_role",
        "role IN ('ADMIN','GOVERNANCE_ANALYST','DATA_OWNER','DATA_STEWARD','REVIEWER')",
    ),
    (
        "data_assets",
        "ck_asset_classification",
        "classification IN ('Public','Internal','Confidential','Restricted')",
    ),
    ("data_assets", "ck_asset_criticality", "criticality IN ('Standard','Critical')"),
    ("data_assets", "ck_asset_status", "status IN ('Active','Retired')"),
    (
        "data_fields",
        "ck_field_classification",
        "classification IN ('Public','Internal','Confidential','Restricted')",
    ),
    (
        "governance_exceptions",
        "ck_exception_status",
        "status IN ('Open','Assigned','Remediation in Progress','Pending Review','Closed','Rejected')",
    ),
    (
        "governance_exceptions",
        "ck_exception_severity",
        "severity IN ('Low','Medium','High','Critical')",
    ),
    ("quality_results", "ck_quality_score", "score >= 0 AND score <= 100"),
    ("control_executions", "ck_control_result", "result IN ('PASS','FAIL','SKIP')"),
    ("evidence", "ck_evidence_status", "status IN ('Pending Review','Approved','Rejected')"),
]


def upgrade():
    for table, name, expression in CONSTRAINTS:
        with op.batch_alter_table(table) as batch:
            batch.create_check_constraint(name, expression)


def downgrade():
    for table, name, expression in reversed(CONSTRAINTS):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
