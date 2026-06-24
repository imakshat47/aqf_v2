from aqf_backend.config import DATASET_DIR
from aqf_backend.models import QueryCondition, QueryRequest
from aqf_backend.services.query_executor import QueryExecutor

executor = QueryExecutor(dataset_dir=DATASET_DIR)
request = QueryRequest(
    conditions=[QueryCondition(field="Secondary Diagnosis", operator="contains", value="Cancer")],
    output_fields=["Secondary Diagnosis", "gender", "Admission type"],
)
result = executor.execute(request)

print()
print("Query Test")
print("----------")
print("Total matches:", result["total_matches"])
print("Rows returned:", len(result["rows"]))
if result["rows"]:
    print("Sample row:")
    print(result["rows"][0])
print()
