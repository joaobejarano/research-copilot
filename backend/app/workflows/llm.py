from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_PROVIDER, OPENAI_API_KEY

TModel = TypeVar("TModel", bound=BaseModel)


class StructuredLLMProvider(Protocol):
    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
    ) -> TModel:
        pass


class OpenAIStructuredLLMProvider:
    def __init__(self, *, model_name: str = LLM_MODEL, api_key: str = OPENAI_API_KEY) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'.")
        if not model_name.strip():
            raise ValueError("LLM_MODEL must not be empty.")

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
    ) -> TModel:
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                },
            },
        )
        payload = _extract_message_content(response)
        return response_model.model_validate_json(payload)


class AnthropicStructuredLLMProvider:
    """Uses Claude's tool-use API to enforce structured JSON output.

    Anthropic does not have a native JSON-schema response mode like OpenAI.
    The idiomatic substitute is tool use with ``tool_choice`` forced to a
    single named tool whose ``input_schema`` is the Pydantic model schema.
    Claude is required to call that tool, so the response is always the
    structured payload — no free-text parsing needed.

    Recommended models: ``claude-haiku-4-5-20251001`` (fast/cheap) or
    ``claude-sonnet-4-6`` (higher quality). Set via the ``LLM_MODEL`` env var.
    """

    def __init__(self, *, model_name: str = LLM_MODEL, api_key: str = ANTHROPIC_API_KEY) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'.")
        if not model_name.strip():
            raise ValueError("LLM_MODEL must not be empty.")

        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
    ) -> TModel:
        tool_name = response_model.__name__
        schema = response_model.model_json_schema()

        response = self._client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Output a structured {tool_name} response.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                return response_model.model_validate(block.input)

        raise ValueError("Anthropic response did not include a tool_use block.")


def _extract_message_content(response: Any) -> str:
    if not getattr(response, "choices", None):
        raise ValueError("LLM response did not include choices.")

    message = response.choices[0].message
    content = getattr(message, "content", None)

    if isinstance(content, str):
        normalized = content.strip()
        if not normalized:
            raise ValueError("LLM response content was empty.")
        return normalized

    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    parts.append(part["text"])
                continue

            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                parts.append(part_text)

        normalized = "".join(parts).strip()
        if normalized:
            return normalized

    raise ValueError("LLM response did not include parseable text content.")


def get_llm_provider(
    provider_name: str = LLM_PROVIDER,
    *,
    model_name: str | None = None,
    api_key: str | None = None,
) -> StructuredLLMProvider:
    normalized_provider = provider_name.strip().lower()
    selected_model_name = model_name if model_name is not None else LLM_MODEL

    if normalized_provider == "openai":
        selected_api_key = api_key if api_key is not None else OPENAI_API_KEY
        return OpenAIStructuredLLMProvider(
            model_name=selected_model_name,
            api_key=selected_api_key,
        )

    if normalized_provider == "anthropic":
        selected_api_key = api_key if api_key is not None else ANTHROPIC_API_KEY
        return AnthropicStructuredLLMProvider(
            model_name=selected_model_name,
            api_key=selected_api_key,
        )

    raise ValueError(f"Unsupported llm provider '{provider_name}'.")
