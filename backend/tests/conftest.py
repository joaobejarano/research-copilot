import os
import shutil
from pathlib import Path
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("STORAGE_DIR", "/tmp/research-copilot-test-storage")

BACKEND_DIR = Path(__file__).resolve().parents[1]
backend_dir_str = str(BACKEND_DIR)

if backend_dir_str not in sys.path:
    sys.path.insert(0, backend_dir_str)


@pytest.fixture(autouse=True)
def reset_test_state() -> None:
    from app.db.database import Base, create_tables, engine

    Base.metadata.drop_all(bind=engine)
    create_tables()
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)

    yield

    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)
