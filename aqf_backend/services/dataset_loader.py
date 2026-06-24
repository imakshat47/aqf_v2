import json
from pathlib import Path


class DatasetLoader:

    def __init__(self, dataset_dir: str):
        self.dataset_dir = Path(dataset_dir)

    def load_records(self):

        records = []

        for file in self.dataset_dir.rglob("*.json"):

            try:

                with open(file, "r", encoding="utf-8") as f:

                    doc = json.load(f)

                    doc["_source_file"] = str(file)

                    records.append(doc)

            except Exception:
                pass

        return records