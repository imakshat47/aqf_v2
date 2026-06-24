from pydantic import BaseModel
from typing import List, Optional, Any


class QueryCondition(BaseModel):
    field_path: str
    operator: str
    value: Any


class QueryRequest(BaseModel):
    conditions: List[QueryCondition]
    return_fields: Optional[List[str]] = []


class QueryResponse(BaseModel):
    total_matches: int
    rows: List[dict]