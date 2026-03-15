import os
from pathlib import Path

APP_NAME = os.getenv("RESEARCH_COPILOT_APP_NAME", "Research Copilot API")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "research_copilot")
POSTGRES_USER = os.getenv("POSTGRES_USER", "research_copilot")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "research_copilot")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    (
        f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    ),
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
storage_dir_value = os.getenv("STORAGE_DIR", "storage/documents")
storage_dir_path = Path(storage_dir_value)

if not storage_dir_path.is_absolute():
    storage_dir_path = PROJECT_ROOT / storage_dir_path

STORAGE_DIR = storage_dir_path.resolve()
