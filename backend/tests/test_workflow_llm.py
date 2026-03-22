import pytest

from app.workflows.llm import OpenAIStructuredLLMProvider, get_llm_provider


def test_get_llm_provider_rejects_unsupported_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported llm provider"):
        get_llm_provider(provider_name="unsupported-provider")


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        OpenAIStructuredLLMProvider(model_name="gpt-4.1-mini", api_key="")


def test_openai_provider_requires_model_name() -> None:
    pytest.importorskip("openai")
    with pytest.raises(ValueError, match="LLM_MODEL must not be empty"):
        OpenAIStructuredLLMProvider(model_name="   ", api_key="test-key")
