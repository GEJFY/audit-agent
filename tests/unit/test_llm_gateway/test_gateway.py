"""LLMゲートウェイ テスト"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm_gateway.gateway import LLMGateway
from src.llm_gateway.providers.base import BaseLLMProvider, LLMResponse


class MockProvider(BaseLLMProvider):
    """テスト用モックプロバイダー"""

    def __init__(self, name: str = "mock", should_fail: bool = False) -> None:
        self._name = name
        self._should_fail = should_fail

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:  # type: ignore[override]
        if self._should_fail:
            raise RuntimeError("プロバイダーエラー")
        return LLMResponse(
            content="モック応答",
            model="mock-model",
            provider=self._name,
            input_tokens=10,
            output_tokens=5,
        )

    async def generate_structured(self, prompt: str, response_schema: dict, **kwargs) -> LLMResponse:  # type: ignore[override]
        return await self.generate(prompt)

    async def health_check(self) -> bool:
        return not self._should_fail


@pytest.mark.unit
class TestLLMGateway:
    """LLMゲートウェイのユニットテスト"""

    async def test_register_and_generate(self) -> None:
        """プロバイダー登録と生成テスト"""
        gateway = LLMGateway()
        gateway.register_provider(MockProvider("test_provider"))

        result = await gateway.generate("テストプロンプト", provider="test_provider")

        assert result.content == "モック応答"
        assert result.provider == "test_provider"

    async def test_fallback(self) -> None:
        """フォールバックテスト"""
        gateway = LLMGateway()
        gateway._fallback_order = ["failing", "working"]

        gateway.register_provider(MockProvider("failing", should_fail=True))
        gateway.register_provider(MockProvider("working"))

        result = await gateway.generate("テスト")

        assert result.provider == "working"

    async def test_health_check(self) -> None:
        """ヘルスチェックテスト"""
        gateway = LLMGateway()
        gateway.register_provider(MockProvider("healthy"))
        gateway.register_provider(MockProvider("unhealthy", should_fail=True))

        results = await gateway.health_check()

        assert results["healthy"] is True
        assert results["unhealthy"] is False

    def test_cost_summary(self) -> None:
        """コストサマリーテスト"""
        gateway = LLMGateway()
        summary = gateway.get_cost_summary()

        assert "total_cost_usd" in summary
        assert "total_tokens" in summary
