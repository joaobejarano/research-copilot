from collections.abc import Sequence
from typing import Any, Protocol

from app.core.config import EMBEDDING_DIMENSION, EMBEDDING_MODEL


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        pass


def _coerce_embedding_vectors(raw_vectors: Any) -> list[list[float]]:
    if hasattr(raw_vectors, "tolist"):
        raw_vectors = raw_vectors.tolist()

    if not isinstance(raw_vectors, list):
        raise ValueError("Embedding model output must be a list-like collection.")

    if raw_vectors and all(isinstance(item, (int, float)) for item in raw_vectors):
        raw_vectors = [raw_vectors]

    embeddings: list[list[float]] = []
    for raw_vector in raw_vectors:
        if hasattr(raw_vector, "tolist"):
            raw_vector = raw_vector.tolist()

        if isinstance(raw_vector, tuple):
            raw_vector = list(raw_vector)

        if not isinstance(raw_vector, list):
            raise ValueError("Each embedding must be a list of numeric values.")

        embeddings.append([float(item) for item in raw_vector])

    return embeddings


class LocalSentenceTransformerProvider:
    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        expected_dimension: int = EMBEDDING_DIMENSION,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.expected_dimension = expected_dimension

        if model is not None:
            self._model = model
            return

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        raw_vectors = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        embeddings = _coerce_embedding_vectors(raw_vectors)

        if len(embeddings) != len(texts):
            raise ValueError(
                "Embedding provider returned a different number of vectors than input texts."
            )

        for index, embedding in enumerate(embeddings):
            if len(embedding) != self.expected_dimension:
                raise ValueError(
                    "Embedding dimension mismatch at index "
                    f"{index}: expected {self.expected_dimension}, got {len(embedding)}."
                )

        return embeddings
