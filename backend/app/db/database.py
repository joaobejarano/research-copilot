from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_pgvector_extension() -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def create_tables() -> None:
    from app.db.models.document import Document  # noqa: F401
    from app.db.models.document_chunk import DocumentChunk  # noqa: F401
    from app.db.models.feedback import Feedback  # noqa: F401

    ensure_pgvector_extension()
    Base.metadata.create_all(bind=engine)


async def get_db() -> AsyncGenerator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
