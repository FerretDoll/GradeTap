from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LLMSettingsBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    provider: str = Field(default="deepseek", max_length=64)
    base_url: str = Field(default="https://api.deepseek.com", alias="baseUrl", max_length=512)
    model: str = Field(default="deepseek-v4-pro", max_length=128)
    temperature: float = Field(default=0.2, ge=0, le=1)
    max_retries: int = Field(default=3, alias="maxRetries", ge=1, le=5)


class LLMSettingsUpdate(LLMSettingsBase):
    api_key: str | None = Field(default=None, alias="apiKey", max_length=4096)


class LLMSettingsRead(LLMSettingsBase):
    api_key: str = Field(default="", alias="apiKey")
    has_api_key: bool = Field(default=False, alias="hasApiKey")
    api_key_mask: str = Field(default="", alias="apiKeyMask")


class LLMSettingsTestResult(BaseModel):
    status: str
    message: str
    provider: str
    model: str
