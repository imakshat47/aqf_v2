from aqf_backend.config import DATASET_DIR, FIELD_STATISTICS_FILE, CLINICAL_INDEX_FILE, QUERYABLE_FIELDS_FILE
from aqf_backend.services.record_loader import RecordLoader
from aqf_backend.services.clinical_index_builder import ClinicalIndexBuilder

loader = RecordLoader()
semantic_records = loader.load_semantic_records(DATASET_DIR)

builder = ClinicalIndexBuilder()
payload = builder.build(
    field_statistics_file=FIELD_STATISTICS_FILE,
    output_file=CLINICAL_INDEX_FILE,
    semantic_records=semantic_records,
    queryable_fields_output=QUERYABLE_FIELDS_FILE,
)

print()
print("Clinical Index Generated")
print("------------------------")
print("Fields:", payload["total_fields"])
print("Index:", CLINICAL_INDEX_FILE)
print("Queryable fields:", QUERYABLE_FIELDS_FILE)
print()
