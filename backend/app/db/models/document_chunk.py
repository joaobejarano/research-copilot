from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.core.config import EMBEDDING_DIMENSION
from app.db.database import Base


class VectorType(UserDefinedType):
    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: object) -> str:
        return f"VECTOR({self.dimensions})"

    def bind_processor(self, _: object):
        def process(value: list[float] | tuple[float, ...] | None) -> str | None:
            if value is None:
                return None

            vector = [float(item) for item in value]
            if len(vector) != self.dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.dimensions}, got {len(vector)}."
                )

            vector_literal = ",".join(format(item, ".15g") for item in vector)
            return f"[{vector_literal}]"

        return process

    def result_processor(self, _: object, __: object):
        def process(
            value: str | bytes | list[float] | tuple[float, ...] | None,
        ) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, list):
                return [float(item) for item in value]
            if isinstance(value, tuple):
                return [float(item) for item in value]
            if isinstance(value, bytes):
                value = value.decode()

            stripped = value.strip().strip("[]")
            if not stripped:
                return []

            return [float(item.strip()) for item in stripped.split(",")]

        return process


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        VectorType(EMBEDDING_DIMENSION), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
