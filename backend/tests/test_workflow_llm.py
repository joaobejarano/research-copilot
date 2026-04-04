import pytest

from app.workflows.llm import AnthropicStructuredLLMProvider, OpenAIStructuredLLMProvider, get_llm_provider


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


def test_get_llm_provider_openai_returns_openai_provider() -> None:
    pytest.importorskip("openai")
    provider = get_llm_provider(provider_name="openai", api_key="test-key")
    assert isinstance(provider, OpenAIStructuredLLMProvider)


def test_anthropic_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        AnthropicStructuredLLMProvider(model_name="claude-haiku-4-5-20251001", api_key="")


def test_anthropic_provider_requires_model_name() -> None:
    pytest.importorskip("anthropic")
    with pytest.raises(ValueError, match="LLM_MODEL must not be empty"):
        AnthropicStructuredLLMProvider(model_name="   ", api_key="test-key")


def test_get_llm_provider_anthropic_returns_anthropic_provider() -> None:
    pytest.importorskip("anthropic")
    provider = get_llm_provider(provider_name="anthropic", api_key="test-key")
    assert isinstance(provider, AnthropicStructuredLLMProvider)


def test_get_llm_provider_anthropic_uses_provided_model_name() -> None:
    pytest.importorskip("anthropic")
    provider = get_llm_provider(
        provider_name="anthropic",
        model_name="claude-sonnet-4-6",
        api_key="test-key",
    )
    assert isinstance(provider, AnthropicStructuredLLMProvider)
    assert provider.model_name == "claude-sonnet-4-6"
