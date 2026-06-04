from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


class EquipmentTagResponse(BaseModel):
    id: UUID
    unit_id: UUID
    unit_name: str
    tag: str
    tag_type: Optional[str]
    description: Optional[str]
    page_number: Optional[int]
    confidence: Optional[float]
    raw_attributes: Optional[dict[str, Any]]
    neighbours: list[str] = Field(default_factory=list)
    source_document: Optional[str] = None


class TagSearchRequest(BaseModel):
    query: str
    unit_id: Optional[UUID] = None
    tag_type: Optional[str] = None
    limit: int = Field(default=20, le=100)


class TagSearchResult(BaseModel):
    tag: str
    tag_type: Optional[str]
    unit_name: str
    description: Optional[str]
    score: float = 1.0


class ProcessPath(BaseModel):
    source_tag: str
    target_tag: str
    path: list[str]
    path_length: int
    connection_types: list[str]
