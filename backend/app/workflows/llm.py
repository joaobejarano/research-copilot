from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import LLM_MODEL, LLM_PROVIDER, OPENAI_API_KEY

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
    selected_api_key = api_key if api_key is not None else OPENAI_API_KEY

    if normalized_provider == "openai":
        return OpenAIStructuredLLMProvider(
            model_name=selected_model_name,
            api_key=selected_api_key,
        )

    raise ValueError(f"Unsupported llm provider '{provider_name}'.")
