from __future__ import annotations

from fastapi import APIRouter

from app.schemas.settings import LLMSettingsRead, LLMSettingsTestResult, LLMSettingsUpdate
from app.services.settings_service import settings_service

router = APIRouter()


@router.get("/llm", response_model=LLMSettingsRead)
def get_llm_settings() -> LLMSettingsRead:
    return settings_service.get_llm_settings()


@router.put("/llm", response_model=LLMSettingsRead)
def update_llm_settings(payload: LLMSettingsUpdate) -> LLMSettingsRead:
    return settings_service.update_llm_settings(payload)


@router.delete("/llm/api-key", response_model=LLMSettingsRead)
def clear_llm_api_key() -> LLMSettingsRead:
    return settings_service.clear_llm_api_key()


@router.post("/llm/test", response_model=LLMSettingsTestResult)
def test_llm_settings() -> LLMSettingsTestResult:
    return settings_service.test_llm_settings()
