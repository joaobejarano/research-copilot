import os
from pathlib import Path
from dotenv import load_dotenv

MODULE_PATH = Path(__file__).resolve()
BACKEND_ROOT = MODULE_PATH.parents[2]
PROJECT_ROOT = MODULE_PATH.parents[3]

# Prefer repo-root .env, but also support backend/.env for local overrides.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}

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

storage_dir_value = os.getenv("STORAGE_DIR", "storage/documents")
storage_dir_path = Path(storage_dir_value)

if not storage_dir_path.is_absolute():
    storage_dir_path = PROJECT_ROOT / storage_dir_path

STORAGE_DIR = storage_dir_path.resolve()

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_MIN_SIMILARITY = float(os.getenv("RETRIEVAL_MIN_SIMILARITY", "0.2"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MAX_WORKFLOW_CITATIONS = int(os.getenv("MAX_WORKFLOW_CITATIONS", "6"))
MAX_WORKFLOW_ITEMS = int(os.getenv("MAX_WORKFLOW_ITEMS", "10"))

CONFIDENCE_PASS_THRESHOLD = float(os.getenv("CONFIDENCE_PASS_THRESHOLD", "0.75"))
CONFIDENCE_REVIEW_THRESHOLD = float(os.getenv("CONFIDENCE_REVIEW_THRESHOLD", "0.50"))
ENABLE_CONFIDENCE_GATING = _get_bool_env("ENABLE_CONFIDENCE_GATING", True)
MAX_AGENT_TOOL_CALLS = int(os.getenv("MAX_AGENT_TOOL_CALLS", "20"))
