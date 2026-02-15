"""LLMプロバイダー基底クラステスト"""

import pytest

from src.llm_gateway.providers.base import BaseLLMProvider, LLMResponse


@pytest.mark.unit
class TestLLMResponse:
    """LLMResponseデータクラスのテスト"""

    def test_defaults(self) -> None:
        """デフォルト値"""
        resp = LLMResponse(content="test", model="m", provider="p")
        assert resp.content == "test"
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.total_tokens == 0
        assert resp.cost_usd == 0.0
        assert resp.latency_ms == 0.0
        assert resp.metadata == {}

    def test_full_fields(self) -> None:
        """全フィールド指定"""
        resp = LLMResponse(
            content="応答テキスト",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            latency_ms=500.0,
            metadata={"stop_reason": "end_turn"},
        )
        assert resp.total_tokens == 150
        assert resp.metadata["stop_reason"] == "end_turn"

    def test_total_cost_jpy(self) -> None:
        """JPY換算プロパティ"""
        resp = LLMResponse(content="", model="m", provider="p", cost_usd=1.0)
        assert resp.total_cost_jpy == 150.0

    def test_total_cost_jpy_zero(self) -> None:
        """コスト0のJPY換算"""
        resp = LLMResponse(content="", model="m", provider="p")
        assert resp.total_cost_jpy == 0.0

    def test_metadata_mutable_default(self) -> None:
        """metadataのデフォルトが共有されない"""
        r1 = LLMResponse(content="", model="m", provider="p")
        r2 = LLMResponse(content="", model="m", provider="p")
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata


@pytest.mark.unit
class TestBaseLLMProvider:
    """BaseLLMProvider ABCのテスト"""

    def test_cannot_instantiate(self) -> None:
        """抽象クラスは直接インスタンス化できない"""
        with pytest.raises(TypeError):
            BaseLLMProvider()  # type: ignore[abstract]

    def test_subclass_must_implement(self) -> None:
        """サブクラスは全メソッドを実装する必要がある"""

        class Incomplete(BaseLLMProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass(self) -> None:
        """全メソッド実装済みサブクラスはインスタンス化できる"""

        class Concrete(BaseLLMProvider):
            @property
            def provider_name(self) -> str:
                return "test"

            async def generate(self, prompt, **kwargs):  # type: ignore[override]
                return LLMResponse(content="ok", model="m", provider="test")

            async def generate_structured(self, prompt, response_schema, **kwargs):  # type: ignore[override]
                return LLMResponse(content="{}", model="m", provider="test")

            async def health_check(self) -> bool:
                return True

        c = Concrete()
        assert c.provider_name == "test"
