"""マルチプロバイダーLLMゲートウェイ — ルーティング + フォールバック + コスト追跡"""

from typing import Any

from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import get_settings
from src.llm_gateway.cost_tracker import CostTracker
from src.llm_gateway.providers.base import BaseLLMProvider, LLMResponse
from src.monitoring.metrics import (
    llm_cost_total,
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)


class LLMGateway:
    """マルチプロバイダーLLMゲートウェイ

    - プライマリ: Anthropic Claude (Sonnet 4.5 / Haiku 4.5)
    - フォールバック: Azure OpenAI
    - 自動リトライ + 指数バックオフ
    - コスト追跡 + メトリクス記録
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}
        self._primary_provider: str = "anthropic"
        self._fallback_order: list[str] = ["anthropic", "azure_openai"]
        self._cost_tracker = CostTracker()
        self._settings = get_settings()

    def register_provider(self, provider: BaseLLMProvider) -> None:
        """プロバイダーを登録"""
        self._providers[provider.provider_name] = provider
        logger.info("LLMプロバイダー登録", provider=provider.provider_name)

    def _get_provider(self, provider_name: str | None = None) -> BaseLLMProvider:
        """プロバイダーを取得"""
        name = provider_name or self._primary_provider
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError(f"プロバイダー '{name}' が未登録")
        return provider

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        use_fast_model: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """テキスト生成 — フォールバック + リトライ対応"""
        if use_fast_model:
            model = self._settings.anthropic_model_fast

        # フォールバックチェーン
        providers_to_try = [provider] if provider else self._fallback_order
        last_error: Exception | None = None

        for provider_name in providers_to_try:
            if provider_name not in self._providers:
                continue
            try:
                llm_provider = self._providers[provider_name]
                response = await llm_provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )

                # メトリクス記録
                self._record_metrics(response)
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    "LLMプロバイダーエラー、フォールバック試行",
                    provider=provider_name,
                    error=str(e),
                )
                continue

        raise last_error or RuntimeError("全LLMプロバイダーが失敗")

    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_prompt: str | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """構造化データ生成"""
        llm_provider = self._get_provider(provider)
        response = await llm_provider.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            system_prompt=system_prompt,
            **kwargs,
        )
        self._record_metrics(response)
        return response

    def _record_metrics(self, response: LLMResponse) -> None:
        """Prometheusメトリクスを記録"""
        llm_requests_total.labels(
            provider=response.provider,
            model=response.model,
            status="success",
        ).inc()

        llm_tokens_total.labels(
            provider=response.provider,
            model=response.model,
            direction="input",
        ).inc(response.input_tokens)

        llm_tokens_total.labels(
            provider=response.provider,
            model=response.model,
            direction="output",
        ).inc(response.output_tokens)

        llm_cost_total.labels(
            provider=response.provider,
            model=response.model,
        ).inc(response.cost_usd)

        llm_request_duration_seconds.labels(
            provider=response.provider,
            model=response.model,
        ).observe(response.latency_ms / 1000)

        # コスト追跡
        self._cost_tracker.record(response)

    async def health_check(self) -> dict[str, bool]:
        """全プロバイダーのヘルスチェック"""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            results[name] = await provider.health_check()
        return results

    def get_cost_summary(self) -> dict[str, Any]:
        """コストサマリーを取得"""
        return self._cost_tracker.get_summary()
