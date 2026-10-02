from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class RecordResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int
    created_at: datetime
    updated_at: datetime


class AssetResponse(RecordResponse):
    name: str
    description: str
    business_domain_id: int
    owner_id: int | None
    steward_id: int | None
    classification: str
    criticality: str
    regulatory_relevance: bool
    source_system: str
    physical_location: str
    status: str
    domain: str | None
    owner: str | None
    steward: str | None
    quality_score: float | None


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
