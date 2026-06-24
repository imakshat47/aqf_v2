from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_DIR = Path(os.getenv("AQF_DATASET_DIR", PROJECT_ROOT / "dataset" / "mixed"))
OUTPUT_DIR = Path(os.getenv("AQF_OUTPUT_DIR", PROJECT_ROOT / "output"))

FIELD_STATISTICS_FILE = Path(os.getenv("AQF_FIELD_STATS_FILE", OUTPUT_DIR / "field_statistics.json"))
CLINICAL_INDEX_FILE = Path(os.getenv("AQF_CLINICAL_INDEX_FILE", OUTPUT_DIR / "clinical_index.json"))
QUERYABLE_FIELDS_FILE = Path(os.getenv("AQF_QUERYABLE_FIELDS_FILE", OUTPUT_DIR / "queryable_fields.json"))
ADAPTIVE_FORM_FILE = Path(os.getenv("AQF_ADAPTIVE_FORM_FILE", OUTPUT_DIR / "adaptive_form.json"))
