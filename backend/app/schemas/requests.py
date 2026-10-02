from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Classification = Literal["Public", "Internal", "Confidential", "Restricted"]
Role = Literal["ADMIN", "GOVERNANCE_ANALYST", "DATA_OWNER", "DATA_STEWARD", "REVIEWER"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    email: str
    password: str


class UserCreate(Input):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=200)
    role: Role
    business_domain_id: int | None = None


class DomainInput(Input):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10)
    active: bool = True


class AssetInput(Input):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(max_length=5000)
    asset_type: Literal[
        "Database Table", "View", "File", "API", "Dataset", "Report", "Data Product"
    ] = "Dataset"
    business_domain_id: int
    owner_id: int | None = None
    steward_id: int | None = None
    classification: Classification = "Internal"
    criticality: Literal["Standard", "Critical"] = "Standard"
    regulatory_relevance: bool = False
    status: Literal["Active", "Retired"] = "Active"
    source_system: str = Field(max_length=120)
    physical_location: str = Field(max_length=240)
    last_reviewed_at: datetime | None = None


class AssetPatch(Input):
    description: str | None = Field(default=None, max_length=5000)
    owner_id: int | None = None
    steward_id: int | None = None
    classification: Classification | None = None
    criticality: Literal["Standard", "Critical"] | None = None
    regulatory_relevance: bool | None = None
    source_system: str | None = Field(default=None, max_length=120)
    physical_location: str | None = Field(default=None, max_length=240)
    last_reviewed_at: datetime | None = None
    status: Literal["Active", "Retired"] | None = None


class FieldInput(Input):
    data_asset_id: int
    name: str = Field(min_length=1, max_length=120)
    data_type: str = Field(min_length=1, max_length=30)
    description: str = Field(max_length=5000)
    nullable: bool = True
    is_cde: bool = False
    classification: Classification
    business_term_id: int | None = None
    regulatory_tag: str | None = Field(default=None, max_length=100)


class TermInput(Input):
    name: str = Field(min_length=2, max_length=160)
    definition: str = Field(min_length=20, max_length=5000)
    business_domain_id: int
    owner_id: int | None = None
    steward_id: int | None = None


class EdgeInput(Input):
    source_asset_id: int
    target_asset_id: int
    source_field_id: int | None = None
    target_field_id: int | None = None
    transformation: str = Field(min_length=10, max_length=5000)


class ExceptionTransition(Input):
    status: Literal["Assigned", "Remediation in Progress", "Pending Review", "Closed", "Rejected"]
    assignee_id: int | None = None
    remediation_plan: str = Field(default="", max_length=5000)


class EvidenceInput(Input):
    exception_id: int
    document_name: str = Field(min_length=3, max_length=200)
    document_type: str = Field(min_length=3, max_length=100)
    local_reference: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=10, max_length=5000)

    @field_validator("local_reference")
    @classmethod
    def safe_reference(cls, value):
        if value.startswith(("/", "http:", "https:")) or ".." in value or "\\" in value:
            raise ValueError("Use a relative evidence reference without traversal")
        return value


class EvidenceReview(Input):
    status: Literal["Approved", "Rejected"]
    notes: str = Field(min_length=10, max_length=5000)


class RunInput(Input):
    run_id: str | None = Field(default=None, min_length=8, max_length=120)


class DatasetRef(Input):
    namespace: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=160)
    facets: dict = Field(default_factory=dict)


class OpenLineageEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    eventType: Literal["START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"]
    eventTime: datetime
    run: dict
    job: dict
    inputs: list[DatasetRef] = Field(default_factory=list)
    outputs: list[DatasetRef] = Field(default_factory=list)
    producer: str


class CleanCustomer(Input):
    customer_id: str = Field(pattern=r"^SYN-C\d{4}$")
    customer_name: str = Field(pattern=r"^Synthetic Customer \d{3}$")
    country: str = Field(pattern=r"^[A-Z]{2}$")
    risk_rating: Literal["LOW", "MEDIUM", "HIGH"]


class CustomerIngestion(Input):
    run_id: str = Field(min_length=8, max_length=120)
    records: list[CleanCustomer] = Field(min_length=1, max_length=10000)


class UserPatch(Input):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    active: bool | None = None
