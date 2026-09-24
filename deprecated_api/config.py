import os
from pathlib import Path

LOCAL_PROJECT_ROOT = Path(__file__).resolve().parent.parent
IS_KAGGLE = Path("/kaggle/input").is_dir()

# nbflow sets this to /kaggle/working in the generated Kaggle notebook.
PROJECT_ROOT = Path(os.environ.get("NBFLOW_PROJECT_ROOT", LOCAL_PROJECT_ROOT))

DATA_DIR = LOCAL_PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

KAGGLE_INPUT_DIR = Path("/kaggle/input")
KAGGLE_WORKING_DIR = Path("/kaggle/working")

INPUT_DIR = KAGGLE_INPUT_DIR if IS_KAGGLE else DATA_DIR
OUTPUT_DIR = KAGGLE_WORKING_DIR if IS_KAGGLE else PROJECT_ROOT
ARTIFACTS_DIR = OUTPUT_DIR / "artifacts"
MODELS_DIR = OUTPUT_DIR / "models"
REPORTS_DIR = OUTPUT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
