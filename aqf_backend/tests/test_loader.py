from aqf_backend.config import DATASET_DIR
from aqf_backend.services.record_loader import RecordLoader

loader = RecordLoader()
records = loader.load_dataset(DATASET_DIR)
print()
print("Loaded Records")
print("----------------")
print(len(records))
print()
if records:
    print("Example Keys")
    print("------------")
    for k in list(records[0].keys())[:25]:
        print(k)
print()
