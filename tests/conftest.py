import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VALIDATION_DIR = ROOT / "data" / "validation"
TESTS_DIR = ROOT / "tests"
