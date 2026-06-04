from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class UnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["CDU"])
    display_name: Optional[str] = None
    description: Optional[str] = None


class UnitResponse(BaseModel):
    id: UUID
    name: str
    display_name: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    tag_count: int = 0
    document_count: int = 0


class UnitStats(BaseModel):
    unit_id: UUID
    unit_name: str
    total_tags: int
    total_documents: int
    total_sop_documents: int
    last_upload: Optional[datetime]
    graph_node_count: int
    graph_edge_count: int
