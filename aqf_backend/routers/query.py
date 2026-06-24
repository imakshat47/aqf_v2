from fastapi import APIRouter

from aqf_backend.models.query_models import (
    QueryRequest,
    QueryResponse
)

from aqf_backend.services.dataset_loader import DatasetLoader

from aqf_backend.services.json_query_executor import (
    JsonQueryExecutor
)

router = APIRouter()

loader = DatasetLoader("dataset/merged")

executor = JsonQueryExecutor()


@router.post(
    "/search",
    response_model=QueryResponse
)
def search_records(
    request: QueryRequest
):

    records = loader.load_records()

    rows = executor.execute(
        records,
        request.conditions,
        request.return_fields
    )

    return QueryResponse(
        total_matches=len(rows),
        rows=rows
    )