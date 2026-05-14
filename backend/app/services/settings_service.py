from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.db.models import SystemSetting
from app.db.session import SessionLocal
from app.schemas.settings import LLMSettingsRead, LLMSettingsTestResult, LLMSettingsUpdate


LLM_SETTINGS_KEY = "llm_settings"

DEFAULT_LLM_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "provider": "deepseek",
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-pro",
    "temperature": 0.2,
    "max_retries": 3,
}


class SettingsService:
    def get_llm_settings(self) -> LLMSettingsRead:
        settings = self.get_llm_settings_dict(include_secret=False)
        return LLMSettingsRead(
            enabled=settings["enabled"],
            provider=settings["provider"],
            baseUrl=settings["base_url"],
            model=settings["model"],
            temperature=settings["temperature"],
            maxRetries=settings["max_retries"],
            apiKey="",
            hasApiKey=bool(settings.get("api_key")),
            apiKeyMask=self._mask_api_key(settings.get("api_key", "")),
        )

    def get_llm_settings_dict(self, include_secret: bool = True) -> dict[str, Any]:
        with SessionLocal() as db:
            setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == LLM_SETTINGS_KEY))
            stored_value = setting.setting_value if setting and isinstance(setting.setting_value, dict) else {}

        settings = {**DEFAULT_LLM_SETTINGS, **stored_value}
        settings["base_url"] = str(settings.get("base_url") or DEFAULT_LLM_SETTINGS["base_url"]).rstrip("/")
        settings["model"] = str(settings.get("model") or DEFAULT_LLM_SETTINGS["model"])
        settings["provider"] = str(settings.get("provider") or DEFAULT_LLM_SETTINGS["provider"])
        settings["api_key"] = str(settings.get("api_key") or "")
        settings["enabled"] = bool(settings.get("enabled"))
        settings["temperature"] = float(settings.get("temperature") or DEFAULT_LLM_SETTINGS["temperature"])
        settings["max_retries"] = int(settings.get("max_retries") or DEFAULT_LLM_SETTINGS["max_retries"])
        if not include_secret:
            return settings
        return settings

    def update_llm_settings(self, payload: LLMSettingsUpdate) -> LLMSettingsRead:
        current = self.get_llm_settings_dict(include_secret=True)
        update_data = payload.model_dump(by_alias=False)
        api_key = update_data.pop("api_key", None)

        next_settings = {
            **current,
            **update_data,
            "base_url": payload.base_url.rstrip("/"),
            "model": payload.model.strip(),
            "provider": payload.provider.strip(),
        }
        if api_key is not None and api_key.strip():
            next_settings["api_key"] = api_key.strip()

        with SessionLocal() as db:
            setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == LLM_SETTINGS_KEY))
            if setting is None:
                setting = SystemSetting(setting_key=LLM_SETTINGS_KEY, setting_value=next_settings)
                db.add(setting)
            else:
                setting.setting_value = next_settings
            db.commit()

        return self.get_llm_settings()

    def clear_llm_api_key(self) -> LLMSettingsRead:
        settings = self.get_llm_settings_dict(include_secret=True)
        settings["api_key"] = ""
        settings["enabled"] = False
        with SessionLocal() as db:
            setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == LLM_SETTINGS_KEY))
            if setting is None:
                setting = SystemSetting(setting_key=LLM_SETTINGS_KEY, setting_value=settings)
                db.add(setting)
            else:
                setting.setting_value = settings
            db.commit()
        return self.get_llm_settings()

    def test_llm_settings(self) -> LLMSettingsTestResult:
        settings = self.get_llm_settings_dict(include_secret=True)
        if not settings["enabled"]:
            return LLMSettingsTestResult(
                status="disabled",
                message="大模型未启用",
                provider=settings["provider"],
                model=settings["model"],
            )
        if not settings["api_key"]:
            return LLMSettingsTestResult(
                status="missing_key",
                message="未配置 API Key",
                provider=settings["provider"],
                model=settings["model"],
            )
        if not settings["base_url"] or not settings["model"]:
            return LLMSettingsTestResult(
                status="unconfigured",
                message="Base URL 或模型未配置",
                provider=settings["provider"],
                model=settings["model"],
            )

        request = Request(
            url=f"{settings['base_url'].rstrip('/')}/chat/completions",
            data=json.dumps(
                {
                    "model": settings["model"],
                    "messages": [
                        {"role": "system", "content": "只回复 OK。"},
                        {"role": "user", "content": "ping"},
                    ],
                    "temperature": 0,
                    "max_tokens": 16,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings['api_key']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            choices = payload.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") if choices else "") or ""
            if choices or payload.get("usage"):
                return LLMSettingsTestResult(
                    status="available",
                    message="密钥可用，模型连接正常",
                    provider=settings["provider"],
                    model=settings["model"],
                )
            return LLMSettingsTestResult(
                status="unavailable",
                message="服务返回为空，请检查模型配置",
                provider=settings["provider"],
                model=settings["model"],
            )
        except HTTPError as exc:
            return LLMSettingsTestResult(
                status="unavailable",
                message=f"模型服务返回 HTTP {exc.code}",
                provider=settings["provider"],
                model=settings["model"],
            )
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            return LLMSettingsTestResult(
                status="unavailable",
                message="模型连接失败，请检查 Base URL、网络或密钥权限",
                provider=settings["provider"],
                model=settings["model"],
            )

    def _mask_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        return "已保存 API Key"


settings_service = SettingsService()
