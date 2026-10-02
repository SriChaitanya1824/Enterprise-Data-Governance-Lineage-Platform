from datetime import datetime, timezone
from uuid import uuid4

from app.governance.engine import CONTROL_DEFINITIONS


def test_authentication_and_roles(client, auth):
    assert client.get("/api/assets").status_code == 401
    assert client.get("/api/assets", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "unknown@example.test", "password": "bad"}
        ).status_code
        == 401
    )
    response = client.get("/api/auth/me", headers=auth())
    assert response.json()["role"] == "GOVERNANCE_ANALYST"
    assert "password_hash" not in response.json()
    assert (
        client.post("/api/governance-controls/run", headers=auth("reviewer"), json={}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/users",
            headers=auth(),
            json={
                "name": "Test User",
                "email": "test@example.test",
                "password": "long-password-123",
                "role": "ADMIN",
            },
        ).status_code
        == 403
    )


def asset_payload(name="test_risk_asset"):
    return {
        "name": name,
        "description": "Synthetic risk asset supporting controlled regulatory reporting.",
        "business_domain_id": 3,
        "classification": "Confidential",
        "criticality": "Critical",
        "regulatory_relevance": True,
        "source_system": "Risk Engine",
        "physical_location": "curated/customer_risk.csv",
        "owner_id": 3,
        "steward_id": 4,
        "last_reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def test_asset_crud_and_validation(client, auth):
    h = auth()
    created = client.post("/api/assets", headers=h, json=asset_payload())
    assert created.status_code == 201, created.text
    aid = created.json()["id"]
    assert client.get(f"/api/assets/{aid}", headers=h).json()["name"] == "test_risk_asset"
    assert client.post("/api/assets", headers=h, json=asset_payload()).status_code == 409
    assert (
        client.patch(f"/api/assets/{aid}", headers=h, json={"classification": "Secret"}).status_code
        == 422
    )
    assert (
        client.patch(f"/api/assets/{aid}", headers=h, json={"description": None}).status_code == 422
    )
    assert (
        client.patch(
            f"/api/assets/{aid}", headers=h, json={"description": "Updated business definition."}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/assets/{aid}", headers=h).json()["status"] == "Retired"
    assert client.get("/api/assets?page=0", headers=h).status_code == 422
    assert client.get("/api/assets/99999", headers=h).status_code == 404


def test_glossary_approval_and_linkage(client, auth):
    h = auth()
    created = client.post(
        "/api/business-terms",
        headers=h,
        json={
            "name": "Exposure at Default",
            "definition": "Outstanding exposure expected at the time of counterparty default.",
            "business_domain_id": 3,
            "owner_id": 3,
            "steward_id": 4,
        },
    )
    assert created.status_code == 201
    tid = created.json()["id"]
    assert client.post(f"/api/business-terms/{tid}/approve", headers=h).status_code == 403
    assert (
        client.post(f"/api/business-terms/{tid}/approve", headers=auth("reviewer")).json()[
            "approval_status"
        ]
        == "Approved"
    )
    assert len(client.get("/api/business-terms/1", headers=h).json()["assets"]) >= 5
    body = {
        "name": "Exposure at Default",
        "definition": "Updated exposure expected at the time of counterparty default.",
        "business_domain_id": 3,
        "owner_id": 3,
        "steward_id": 4,
    }
    assert (
        client.put(f"/api/business-terms/{tid}", headers=h, json=body).json()["approval_status"]
        == "Draft"
    )


def test_cde_profiles_and_classification(client, auth):
    h = auth()
    response = client.get("/api/cdes?q=risk_rating&domain_id=3", headers=h).json()
    assert response["total"] == 3
    cid = response["items"][0]["id"]
    detail = client.get(f"/api/cdes/{cid}", headers=h).json()
    assert detail["business_term"]["name"] == "Customer Risk Rating"
    assert detail["quality_rules"] and detail["lineage"]["edges"]
    aid = detail["asset"]["id"]
    assert (
        client.patch(f"/api/assets/{aid}", headers=h, json={"classification": "Public"}).status_code
        == 422
    )
    created = client.post(
        "/api/fields",
        headers=h,
        json={
            "data_asset_id": aid,
            "name": "restricted_id",
            "data_type": "string",
            "description": "Restricted personal identifier",
            "classification": "Restricted",
            "is_cde": True,
        },
    )
    assert created.status_code == 422


def test_lineage_directions_cycles_and_field_scope(client, auth):
    h = auth()
    assets = client.get("/api/assets?page_size=100", headers=h).json()["items"]
    ids = {a["name"]: a["id"] for a in assets}
    aid = ids["customer_risk"]
    upstream = client.get(f"/api/lineage/upstream/{aid}", headers=h).json()
    downstream = client.get(f"/api/lineage/downstream/{aid}", headers=h).json()
    assert any(n["name"] == "customer_raw" for n in upstream["nodes"])
    assert not any(n["name"] == "regulatory_customer_report" for n in upstream["nodes"])
    assert any(n["name"] == "regulatory_customer_report" for n in downstream["nodes"])
    response = client.post(
        "/api/lineage/edges",
        headers=h,
        json={
            "source_asset_id": ids["regulatory_customer_report"],
            "target_asset_id": ids["customer_raw"],
            "transformation": "Invalid circular dependency",
        },
    )
    assert response.status_code == 422
    cde = client.get("/api/cdes?q=risk_rating&domain_id=3", headers=h).json()["items"][0]
    assert client.get(f'/api/lineage/fields/{cde["id"]}', headers=h).json()["scope"] == "field"


def test_openlineage_idempotency(client, auth):
    h = auth()
    event = {
        "eventType": "COMPLETE",
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "run": {"runId": str(uuid4())},
        "job": {"namespace": "enterprise", "name": "metadata_sync"},
        "inputs": [{"namespace": "CRM", "name": "customer_raw"}],
        "outputs": [{"namespace": "Customer Master", "name": "customer_clean"}],
        "producer": "https://openlineage.io",
    }
    response = client.post("/api/lineage/events", headers=h, json=event)
    assert response.status_code == 200, response.text
    assert response.json()["edges_captured"] == 1
    assert client.post("/api/lineage/events", headers=h, json=event).json()["duplicate"] is True
    event["run"]["runId"] = str(uuid4())
    event["inputs"][0]["namespace"] = "Wrong namespace"
    assert client.post("/api/lineage/events", headers=h, json=event).status_code == 422


def test_quality_observed_not_random(client, auth):
    h = auth()
    assets = client.get("/api/assets?page_size=100", headers=h).json()["items"]
    scores = {a["name"]: a["quality_score"] for a in assets}
    assert scores["customer_risk"] == 100
    assert 95 < scores["customer_raw"] < 100
    results = client.get("/api/data-quality/results", headers=h).json()["items"]
    assert any(not r["passed"] and r["actual_result"]["unexpected_count"] == 1 for r in results)
    response = client.post(
        "/api/data-quality/run", headers=h, json={"run_id": "initial-quality-baseline"}
    )
    assert response.json()["duplicate"] is True


def test_control_deduplication_and_metrics(client, auth):
    h = auth()
    assert client.get("/api/governance-controls", headers=h).json()["total"] == len(
        CONTROL_DEFINITIONS
    )
    before = client.get("/api/exceptions", headers=h).json()["total"]
    response = client.post(
        "/api/governance-controls/run", headers=h, json={"run_id": "repeat-control-run"}
    )
    assert response.json()["failures"] > 0
    assert client.get("/api/exceptions", headers=h).json()["total"] == before
    assert client.post(
        "/api/governance-controls/run", headers=h, json={"run_id": "repeat-control-run"}
    ).json()["duplicate"]
    dashboard = client.get("/api/dashboard", headers=h).json()
    assert dashboard["total_assets"] == 13 and dashboard["missing_ownership"] == 1
    assert dashboard["quality_coverage"] == 13
    risk = next(r for r in dashboard["adoption"] if r["domain"] == "Risk Management")
    assert risk["ownership"] == 66.7
    assert client.get("/api/audit", headers=h).json()["total"] > 100
    assert client.delete("/api/exceptions/1", headers=h).status_code == 405


def test_end_to_end_missing_cde_lineage_remediation(client, auth):
    analyst, reviewer, owner = auth(), auth("reviewer"), auth("data_owner")
    created = client.post(
        "/api/assets", headers=analyst, json=asset_payload("new_regulatory_risk")
    ).json()
    aid = created["id"]
    field = client.post(
        "/api/fields",
        headers=analyst,
        json={
            "data_asset_id": aid,
            "name": "risk_rating",
            "data_type": "string",
            "description": "Approved customer risk classification for the reporting population.",
            "classification": "Confidential",
            "is_cde": True,
            "business_term_id": 1,
        },
    ).json()
    client.post("/api/governance-controls/run", headers=analyst, json={})
    controls = client.get("/api/governance-controls", headers=analyst).json()["items"]
    lineage_control = next(c["id"] for c in controls if c["code"] == "LINEAGE")
    exceptions = client.get("/api/exceptions?page_size=100", headers=analyst).json()["items"]
    exception = next(
        e for e in exceptions if e["data_asset_id"] == aid and e["control_id"] == lineage_control
    )
    eid = exception["id"]
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition", headers=reviewer, json={"status": "Closed"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition",
            headers=analyst,
            json={"status": "Assigned", "assignee_id": 3},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition",
            headers=owner,
            json={
                "status": "Remediation in Progress",
                "remediation_plan": "Document customer risk field mapping and verify upstream traceability.",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition", headers=owner, json={"status": "Pending Review"}
        ).status_code
        == 409
    )
    source = client.get(
        "/api/cdes?q=risk_rating&domain_id=3&page_size=100", headers=analyst
    ).json()["items"][0]
    edge = client.post(
        "/api/lineage/edges",
        headers=analyst,
        json={
            "source_asset_id": source["data_asset_id"],
            "target_asset_id": aid,
            "source_field_id": source["id"],
            "target_field_id": field["id"],
            "transformation": "Project approved risk_rating into the regulatory data product.",
        },
    )
    assert edge.status_code == 201, edge.text
    evidence = client.post(
        "/api/evidence",
        headers=owner,
        json={
            "exception_id": eid,
            "document_name": "lineage-validation.pdf",
            "document_type": "Lineage Validation",
            "local_reference": "private/lineage-validation.pdf",
            "description": "Documented field mapping and verified upstream traceability.",
        },
    )
    assert evidence.status_code == 201
    evid = evidence.json()["id"]
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition", headers=owner, json={"status": "Pending Review"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/evidence/{evid}/review",
            headers=owner,
            json={"status": "Approved", "notes": "I approve my own evidence."},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/evidence/{evid}/review",
            headers=reviewer,
            json={
                "status": "Approved",
                "notes": "Verified the documented mapping and passing lineage control.",
            },
        ).status_code
        == 200
    )
    closed = client.post(
        f"/api/exceptions/{eid}/transition", headers=reviewer, json={"status": "Closed"}
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["closed_at"]
    history = client.get(f"/api/exceptions/{eid}", headers=reviewer).json()["history"]
    assert len(history) == 5
    client.delete(f'/api/lineage/edges/{edge.json()["id"]}', headers=analyst)
    client.post("/api/governance-controls/run", headers=analyst, json={})
    items = client.get("/api/exceptions?page_size=100", headers=analyst).json()["items"]
    assert (
        len([e for e in items if e["data_asset_id"] == aid and e["control_id"] == lineage_control])
        == 2
    )


def test_ownership_scope_and_evidence_security(client, auth):
    h = auth("data_owner")
    assert client.patch("/api/assets/7", headers=h, json={"owner_id": 3}).status_code == 403
    assert (
        client.patch(
            "/api/assets/1", headers=h, json={"description": "Owner-reviewed metadata definition."}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/evidence",
            headers=auth(),
            json={
                "exception_id": 1,
                "document_name": "secret.pdf",
                "document_type": "Document",
                "local_reference": "../secret.pdf",
                "description": "Attempt a traversal reference.",
            },
        ).status_code
        == 422
    )
    assert client.get("/api/search?q=risk", headers=auth()).json()["items"]
    assert client.patch("/api/audit/1", headers=auth("admin"), json={}).status_code == 404


def test_user_access_revocation_and_assignment_scope(client, auth):
    admin, owner = auth("admin"), auth("data_owner")
    assert client.patch("/api/users/3", headers=auth(), json={"active": False}).status_code == 403
    assert client.patch("/api/users/1", headers=admin, json={"active": False}).status_code == 409
    assert client.patch("/api/users/3", headers=admin, json={"active": False}).status_code == 200
    assert client.get("/api/assets", headers=owner).status_code == 401


def test_closure_requires_actual_remediation(client, auth):
    analyst, reviewer = auth(), auth("reviewer")
    controls = client.get("/api/governance-controls", headers=analyst).json()["items"]
    ownership_id = next(c["id"] for c in controls if c["code"] == "OWNERSHIP")
    exception = next(
        e
        for e in client.get("/api/exceptions", headers=analyst).json()["items"]
        if e["control_id"] == ownership_id
    )
    eid = exception["id"]
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition",
            headers=analyst,
            json={"status": "Assigned", "assignee_id": 3},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/exceptions/{eid}/transition",
            headers=analyst,
            json={
                "status": "Remediation in Progress",
                "remediation_plan": "Obtain risk ownership attestation and verify assignment.",
            },
        ).status_code
        == 200
    )
    evidence = client.post(
        "/api/evidence",
        headers=analyst,
        json={
            "exception_id": eid,
            "document_name": "unverified.pdf",
            "document_type": "Ownership Attestation",
            "local_reference": "private/unverified.pdf",
            "description": "Document alone must not bypass the missing owner policy.",
        },
    ).json()
    client.post(
        f"/api/exceptions/{eid}/transition", headers=analyst, json={"status": "Pending Review"}
    )
    client.post(
        f'/api/evidence/{evidence["id"]}/review',
        headers=reviewer,
        json={
            "status": "Approved",
            "notes": "Document inspected, but ownership assignment must still be checked.",
        },
    )
    response = client.post(
        f"/api/exceptions/{eid}/transition", headers=reviewer, json={"status": "Closed"}
    )
    assert response.status_code == 409
    assert "must pass" in response.json()["detail"]


def test_synthetic_ingestion_and_private_path_validation(client, auth, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "data_root", tmp_path)
    h = auth()
    body = {
        "run_id": "synthetic-ingestion-test",
        "records": [
            {
                "customer_id": "SYN-C0001",
                "customer_name": "Synthetic Customer 001",
                "country": "DE",
                "risk_rating": "LOW",
            }
        ],
    }
    response = client.post("/api/ingestion/customer-clean", headers=h, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["rows"] == 1
    assert (
        (tmp_path / "curated/customer_clean.csv")
        .read_text()
        .startswith("customer_id,customer_name")
    )
    body["records"][0]["customer_name"] = "Real customer name"
    assert client.post("/api/ingestion/customer-clean", headers=h, json=body).status_code == 422
