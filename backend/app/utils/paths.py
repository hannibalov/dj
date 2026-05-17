from pathlib import Path

# backend/app/utils/paths.py -> repo root is three levels up
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"


def sqlite_url_for(db_filename: str = "dj_library.db") -> str:
    return f"sqlite:///{DATA_DIR / db_filename}"
