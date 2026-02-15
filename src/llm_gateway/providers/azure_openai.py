"""Azure OpenAI プロバイダー — フォールバック用"""

import time
from typing import Any

from loguru import logger

from src.config.settings import get_settings
from src.llm_gateway.providers.base import BaseLLMProvider, LLMResponse


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI API プロバイダー（フォールバック用）"""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.azure_openai_api_key
        self._endpoint = settings.azure_openai_endpoint
        self._api_version = settings.azure_openai_api_version
        self._deployment = settings.azure_openai_deployment
        self._client: Any = None

    def _get_client(self) -> Any:
        """遅延初期化でクライアントを取得"""
        if self._client is None:
            try:
                from openai import AsyncAzureOpenAI

                self._client = AsyncAzureOpenAI(
                    api_key=self._api_key,
                    azure_endpoint=self._endpoint,
                    api_version=self._api_version,
                )
            except ImportError:
                logger.warning("openai パッケージ未インストール — Azure OpenAI フォールバック無効")
                raise
        return self._client

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Azure OpenAI APIでテキスト生成"""
        client = self._get_client()
        deployment = model or self._deployment

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        try:
            response = await client.chat.completions.create(
                model=deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            latency_ms = (time.monotonic() - start) * 1000
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=deployment,
                provider="azure_openai",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                cost_usd=0.0,  # Azure pricing varies
                latency_ms=latency_ms,
                metadata={"finish_reason": choice.finish_reason},
            )
        except Exception as e:
            logger.error("Azure OpenAI API エラー", error=str(e))
            raise

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """構造化データ生成"""
        import json

        schema_instruction = f"Respond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"
        combined_system = f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction
        return await self.generate(prompt=prompt, system_prompt=combined_system, model=model, **kwargs)

    async def health_check(self) -> bool:
        """接続チェック"""
        if not self._api_key or not self._endpoint:
            return False
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self._deployment,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return len(response.choices) > 0
        except Exception:
            return False
