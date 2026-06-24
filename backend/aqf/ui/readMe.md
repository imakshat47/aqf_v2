PART 8: Configuration & Entry Points
Python
# aqf/config/settings.py
"""AQF Configuration"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / ".cache"

DEFAULT_SLICE_SIZE = 1000
DEFAULT_RESULT_LIMIT = 100
DEFAULT_OCCURRENCE_SEMANTICS = "ALL"
Python
# run_api.py
#!/usr/bin/env python3
"""Run AQF API server"""
import uvicorn
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    uvicorn.run("aqf.api.main:app", host="0.0.0.0", port=8000, reload=True)
Python
# run_ui.py
#!/usr/bin/env python3
"""Run AQF Streamlit UI"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    subprocess.run([sys.executable, "-m", "streamlit", "run", "aqf/ui/app.py"])
PART 9: requirements.txt
txt
# AQF Unified Pipeline
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
streamlit==1.30.0
pandas==2.1.4
numpy==1.26.3
requests==2.31.0
python-multipart==0.0.6
How to Run the Unified Pipeline
bash
# 1. Setup
cd aqf_unified
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Copy your JSON files
mkdir -p data
cp /path/to/your/*.json data/

# 3. Terminal 1 - Start API
python run_api.py

# 4. Terminal 2 - Start UI
python run_ui.py

# 5. Open browser
# API Docs: http://localhost:8000/docs
# Streamlit UI: http://localhost:8501
