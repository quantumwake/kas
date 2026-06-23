"""Pydantic models for the Anthropic Messages API surface we implement.

Only the subset needed for text + tool-use agentic loops. Unknown fields
(cache_control, metadata, thinking, ...) are accepted and ignored so official
Anthropic SDK clients work unmodified.
"""

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Hard ceiling on requested output tokens: bounds a single request's compute so
# a caller can't pin the GPU with max_tokens=10_000_000. Generous enough for any
# real agentic turn; override with KAS_MAX_OUTPUT_TOKENS. Over-cap requests fail
# Pydantic validation -> the Anthropic error envelope (RequestValidationError).
MAX_OUTPUT_TOKENS = int(os.environ.get("KAS_MAX_OUTPUT_TOKENS", str(128 * 1024)))


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | list[dict[str, Any]] | None = None
    is_error: bool = False


class ThinkingBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str = ""


ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock | ThinkingBlock


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: Literal["user", "assistant"]
    content: str | list[ContentBlock]


class ToolDef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: str = ""
    input_schema: dict[str, Any]


class MessagesRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    model: str
    max_tokens: int = Field(1024, ge=1, le=MAX_OUTPUT_TOKENS)
    messages: list[Message]
    system: str | list[dict[str, Any]] | None = None
    tools: list[ToolDef] = []
    tool_choice: dict[str, Any] | None = None
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    stop_sequences: list[str] = []
    thinking: dict[str, Any] | None = None

    @property
    def thinking_enabled(self) -> bool:
        return (self.thinking or {}).get("type") in ("adaptive", "enabled")
