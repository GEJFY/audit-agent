"""Anthropic Claude プロバイダー — Sonnet 4.5 / Haiku 4.5"""

import time
from typing import Any

import anthropic
from loguru import logger

from src.config.settings import get_settings
from src.llm_gateway.providers.base import BaseLLMProvider, LLMResponse

# Claude料金表（USD per 1M tokens）
CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
}


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API プロバイダー"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout,
        )
        self._default_model = settings.anthropic_model_primary
        self._fast_model = settings.anthropic_model_fast
        self._max_tokens = settings.anthropic_max_tokens

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """コスト計算（USD）"""
        pricing = CLAUDE_PRICING.get(model, {"input": 3.0, "output": 15.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Claude APIでテキスト生成"""
        model = model or self._default_model
        max_tokens = max_tokens or self._max_tokens

        messages = [{"role": "user", "content": prompt}]

        start = time.monotonic()
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=messages,  # type: ignore[arg-type]
                **kwargs,
            )

            latency_ms = (time.monotonic() - start) * 1000
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            content = response.content[0].text if response.content else ""  # type: ignore[union-attr]

            logger.debug(
                "LLM生成完了",
                provider="anthropic",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(latency_ms, 1),
            )

            return LLMResponse(
                content=content,
                model=model,
                provider="anthropic",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=self._calculate_cost(model, input_tokens, output_tokens),
                latency_ms=latency_ms,
                metadata={"stop_reason": response.stop_reason},
            )

        except anthropic.APIError as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("Anthropic API エラー", error=str(e), model=model, latency_ms=latency_ms)
            raise

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """構造化データ生成 — JSONスキーマに従った出力"""
        import json

        schema_instruction = (
            f"以下のJSONスキーマに厳密に従ってJSON形式で回答してください。"
            f"JSONのみを出力し、それ以外のテキストは含めないでください。\n\n"
            f"スキーマ:\n{json.dumps(response_schema, ensure_ascii=False, indent=2)}"
        )

        combined_system = f"{system_prompt}\n\n{schema_instruction}" if system_prompt else schema_instruction

        return await self.generate(
            prompt=prompt,
            system_prompt=combined_system,
            model=model,
            **kwargs,
        )

    async def generate_fast(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Haikuモデルで高速生成（軽量タスク用）"""
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self._fast_model,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Anthropic API接続チェック"""
        try:
            response = await self._client.messages.create(
                model=self._fast_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return len(response.content) > 0
        except Exception as e:
            logger.error("Anthropic ヘルスチェック失敗", error=str(e))
            return False
