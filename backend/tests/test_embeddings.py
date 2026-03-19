import pytest

from app.ingestion.embeddings import LocalSentenceTransformerProvider


class FakeSentenceModel:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[dict[str, object]] = []

    def encode(self, texts: list[str], **kwargs: object) -> list[list[float]]:
        self.calls.append({"texts": texts, "kwargs": kwargs})
        return self.vectors


def test_local_provider_returns_embeddings_from_model_output() -> None:
    fake_model = FakeSentenceModel(
        vectors=[
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
    )
    provider = LocalSentenceTransformerProvider(
        model_name="fake-model",
        expected_dimension=3,
        model=fake_model,
    )

    embeddings = provider.embed_texts(["first", "second"])

    assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert fake_model.calls[0]["texts"] == ["first", "second"]


def test_local_provider_raises_for_dimension_mismatch() -> None:
    provider = LocalSentenceTransformerProvider(
        model_name="fake-model",
        expected_dimension=3,
        model=FakeSentenceModel(vectors=[[0.1, 0.2]]),
    )

    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        provider.embed_texts(["first"])


def test_local_provider_raises_for_vector_count_mismatch() -> None:
    provider = LocalSentenceTransformerProvider(
        model_name="fake-model",
        expected_dimension=3,
        model=FakeSentenceModel(vectors=[[0.1, 0.2, 0.3]]),
    )

    with pytest.raises(ValueError, match="different number of vectors"):
        provider.embed_texts(["first", "second"])
