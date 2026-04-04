from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MCPToolErrorPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=800)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = MODEL_CONFIG


class MCPToolError(ValueError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = MCPToolErrorPayload(
            code=code,
            message=message,
            retryable=retryable,
            details=details or {},
        )
        self.payload = payload
        super().__init__(payload.model_dump_json())


def raise_mcp_tool_error(
    *,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> None:
    raise MCPToolError(
        code=code,
        message=message,
        retryable=retryable,
        details=details,
    )
