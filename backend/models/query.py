from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any


class NLQueryRequest(BaseModel):
    question: str
    unit_id: Optional[UUID] = None
    include_cross_unit: bool = False
    chat_history: list[dict[str, Any]] = []
    drawing_ids: list[str] = []   # empty = all drawings; non-empty = restrict to these doc IDs


class NLQueryResponse(BaseModel):
    answer: str
    query_type: str           # list | detail | path | impact | sop
    data: Optional[Any] = None
    sources: list[dict[str, str]] = []
    confidence: float = 1.0
    unit_context: Optional[str] = None


class BugReportRequest(BaseModel):
    component: str
    description: str
    steps_to_reproduce: str
    severity: str
    unit_name: Optional[str] = None
    page_context: Optional[str] = None
