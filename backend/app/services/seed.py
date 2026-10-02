from datetime import timedelta
from typing import Any

import pycountry
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import passwords
from app.governance.engine import CONTROL_DEFINITIONS, execute_controls
from app.models.entities import (
    BusinessDomain,
    BusinessTerm,
    DataAsset,
    DataField,
    GovernanceControl,
    LineageEdge,
    Person,
    QualityRule,
    now,
)
from app.quality.service import execute_quality
from app.services.audit import audit

ASSETS = [
    ("customer_raw", "Retail Banking", "CRM", "raw/customers.csv", "File", False),
    (
        "customer_clean",
        "Retail Banking",
        "Customer Master",
        "curated/customer_clean.csv",
        "Dataset",
        False,
    ),
    (
        "customer_master",
        "Retail Banking",
        "Customer Master",
        "curated/customer_master.csv",
        "Database Table",
        False,
    ),
    (
        "account_master",
        "Retail Banking",
        "Core Banking",
        "sample/accounts.csv",
        "Database Table",
        False,
    ),
    ("transaction_raw", "Operations", "Payments", "raw/transactions.csv", "File", False),
    (
        "transaction_clean",
        "Operations",
        "Payments",
        "curated/transaction_clean.csv",
        "Dataset",
        False,
    ),
    (
        "customer_risk",
        "Risk Management",
        "Risk Engine",
        "curated/customer_risk.csv",
        "Dataset",
        True,
    ),
    (
        "credit_risk_dataset",
        "Risk Management",
        "Risk Engine",
        "curated/credit_risk_dataset.csv",
        "Dataset",
        True,
    ),
    (
        "regulatory_customer_report",
        "Risk Management",
        "Regulatory Reporting",
        "curated/regulatory_customer_report.csv",
        "Report",
        True,
    ),
    (
        "regulatory_transaction_report",
        "Finance",
        "Finance ERP",
        "curated/regulatory_transaction_report.csv",
        "Report",
        True,
    ),
    ("finance_ledger", "Finance", "Finance ERP", "sample/ledger.csv", "Database Table", False),
    (
        "corporate_exposure",
        "Corporate Banking",
        "Core Banking",
        "sample/exposures.csv",
        "Dataset",
        True,
    ),
    ("treasury_positions", "Treasury", "Treasury Engine", "sample/positions.csv", "Dataset", False),
]


def seed(db):
    if db.scalar(select(BusinessDomain)):
        return {"seeded": False, "reason": "Catalog already exists; seed is non-destructive"}
    domains = {}
    for name in [
        "Retail Banking",
        "Corporate Banking",
        "Risk Management",
        "Finance",
        "Operations",
        "Treasury",
    ]:
        domain = BusinessDomain(
            name=name,
            description=f"Accountable business division for {name.lower()} data products.",
        )
        db.add(domain)
        db.flush()
        domains[name] = domain
    users = {}
    names = {
        "ADMIN": "Platform Administrator",
        "GOVERNANCE_ANALYST": "Governance Analyst",
        "DATA_OWNER": "Risk Data Owner",
        "DATA_STEWARD": "Customer Risk Steward",
        "REVIEWER": "Independent Compliance Reviewer",
    }
    hash_value = passwords.hash(get_settings().bootstrap_password)
    for role, name in names.items():
        user = Person(
            name=name,
            email=f"{role.lower()}@example.test",
            role=role,
            business_domain_id=domains["Risk Management"].id,
            password_hash=hash_value,
        )
        db.add(user)
        db.flush()
        users[role] = user
    terms = {}
    for name, definition in [
        (
            "Customer Risk Rating",
            "Risk classification assigned to a customer using approved risk assessment rules; LOW, MEDIUM or HIGH.",
        ),
        (
            "Customer",
            "Synthetic legal or natural person with a banking relationship identified by a stable customer identifier.",
        ),
        (
            "Transaction Amount",
            "Gross monetary amount of a financial transaction denominated in the recorded transaction currency.",
        ),
        (
            "Regulatory Reporting Date",
            "Business date at which the regulatory report reflects the institution's reporting population.",
        ),
    ]:
        term = BusinessTerm(
            name=name,
            definition=definition,
            business_domain_id=domains["Risk Management"].id,
            owner_id=users["DATA_OWNER"].id,
            steward_id=users["DATA_STEWARD"].id,
            approval_status="Approved",
        )
        db.add(term)
        db.flush()
        terms[name] = term
    assets: dict[str, DataAsset] = {}
    fields: dict[str, dict[str, DataField]] = {}
    for name, domain_name, system, location, asset_type, regulatory in ASSETS:
        asset = DataAsset(
            name=name,
            description=f"Synthetic {name.replace('_', ' ')} supporting controlled banking analytics and traceability.",
            asset_type=asset_type,
            business_domain_id=domains[domain_name].id,
            owner_id=None if name == "customer_risk" else users["DATA_OWNER"].id,
            steward_id=users["DATA_STEWARD"].id,
            classification="Confidential",
            criticality="Critical",
            regulatory_relevance=regulatory,
            source_system=system,
            physical_location=location,
            last_reviewed_at=now() - timedelta(days=120 if name == "finance_ledger" else 20),
        )
        db.add(asset)
        db.flush()
        assets[name] = asset
        if "transaction" in name:
            columns = ["transaction_id", "account_id", "transaction_amount", "transaction_date"]
        elif name == "account_master":
            columns = ["account_id", "customer_id", "product_type"]
        elif name in {"finance_ledger", "corporate_exposure", "treasury_positions"}:
            columns = ["account_id", "transaction_amount", "business_date"]
        else:
            columns = ["customer_id", "customer_name", "country", "risk_rating"]
        fields[name] = {}
        for column in columns:
            linked_term = (
                terms["Customer Risk Rating"]
                if column == "risk_rating"
                else (
                    terms["Transaction Amount"]
                    if column == "transaction_amount"
                    else terms["Customer"] if column == "customer_id" else None
                )
            )
            field = DataField(
                data_asset_id=asset.id,
                name=column,
                data_type=(
                    "decimal"
                    if column == "transaction_amount"
                    else "date" if "date" in column else "string"
                ),
                description=(
                    term.definition
                    if term
                    else f"Documented {column.replace('_', ' ')} for {name}."
                ),
                nullable=False,
                is_cde=column in {"risk_rating", "transaction_amount"},
                classification="Confidential",
                business_term_id=linked_term.id if linked_term else None,
                regulatory_tag="BCBS239" if regulatory else None,
            )
            db.add(field)
            db.flush()
            fields[name][column] = field
            expectation_params: list[tuple[str, dict[str, Any]]] = [
                ("ExpectColumnValuesToNotBeNull", {"column": column})
            ]
            if column in {"customer_id", "transaction_id", "account_id"}:
                expectation_params.append(("ExpectColumnValuesToBeUnique", {"column": column}))
            if column == "risk_rating":
                expectation_params.append(
                    (
                        "ExpectColumnValuesToBeInSet",
                        {"column": column, "value_set": ["LOW", "MEDIUM", "HIGH"]},
                    )
                )
            if column == "country":
                expectation_params.append(
                    (
                        "ExpectColumnValuesToBeInSet",
                        {
                            "column": column,
                            "value_set": sorted(c.alpha_2 for c in pycountry.countries),
                        },
                    )
                )
            if column == "transaction_amount":
                expectation_params.append(
                    ("ExpectColumnValuesToBeBetween", {"column": column, "min_value": 0})
                )
            for exp, params in expectation_params:
                db.add(
                    QualityRule(
                        data_asset_id=asset.id,
                        field_id=field.id,
                        name=f"{column}: {exp.removeprefix('ExpectColumnValuesTo')}",
                        expectation=exp,
                        parameters=params,
                        severity="High",
                    )
                )
    paths = [
        ("customer_raw", "customer_clean", "Trim names and normalize risk and country codes"),
        ("customer_clean", "customer_master", "Deduplicate stable customer identifiers"),
        ("customer_master", "customer_risk", "Apply approved risk classification rules"),
        ("customer_risk", "credit_risk_dataset", "Project customer risk data for risk analytics"),
        (
            "credit_risk_dataset",
            "regulatory_customer_report",
            "Project approved regulatory reporting population",
        ),
        ("transaction_raw", "transaction_clean", "Normalize payments and reject negative amounts"),
        (
            "transaction_clean",
            "regulatory_transaction_report",
            "Project payment reporting population",
        ),
    ]
    for src, dst, transformation in paths:
        db.add(
            LineageEdge(
                source_asset_id=assets[src].id,
                target_asset_id=assets[dst].id,
                edge_key="dataset",
                transformation=transformation,
            )
        )
        for column in set(fields[src]) & set(fields[dst]):
            source, target = fields[src][column], fields[dst][column]
            db.add(
                LineageEdge(
                    source_asset_id=assets[src].id,
                    target_asset_id=assets[dst].id,
                    source_field_id=source.id,
                    target_field_id=target.id,
                    edge_key=f"field:{source.id}:{target.id}",
                    transformation=f"{column}: {transformation}",
                )
            )
    for code, name, description, severity in CONTROL_DEFINITIONS:
        db.add(GovernanceControl(code=code, name=name, description=description, severity=severity))
    db.flush()
    audit(db, users["ADMIN"], "Synthetic catalog seeded", domains["Risk Management"])
    execute_quality(db, users["ADMIN"], run_id="initial-quality-baseline")
    execute_controls(db, users["ADMIN"], run_id="initial-control-baseline")
    return {"seeded": True, "assets": len(assets)}
