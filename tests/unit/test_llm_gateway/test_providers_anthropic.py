"""Anthropic Claudeプロバイダーテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm_gateway.providers.base import LLMResponse


@pytest.mark.unit
class TestAnthropicProvider:
    """AnthropicProviderのテスト"""

    @pytest.fixture
    def provider(self) -> "AnthropicProvider":  # noqa: F821
        """モック設定でプロバイダーを作成"""
        with patch("src.llm_gateway.providers.anthropic.get_settings") as mock_settings:
            settings = MagicMock()
            settings.anthropic_api_key = "sk-ant-test"
            settings.anthropic_timeout = 30
            settings.anthropic_model_primary = "claude-sonnet-4-5-20250929"
            settings.anthropic_model_fast = "claude-haiku-4-5-20251001"
            settings.anthropic_max_tokens = 4096
            mock_settings.return_value = settings

            with patch("src.llm_gateway.providers.anthropic.anthropic") as mock_anthropic:
                mock_anthropic.AsyncAnthropic.return_value = AsyncMock()
                from src.llm_gateway.providers.anthropic import AnthropicProvider

                p = AnthropicProvider()
                return p

    def test_provider_name(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """プロバイダー名"""
        assert provider.provider_name == "anthropic"

    def test_calculate_cost_sonnet(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """Sonnetのコスト計算"""
        cost = provider._calculate_cost("claude-sonnet-4-5-20250929", 1_000_000, 1_000_000)
        # input: 3.0, output: 15.0 → 18.0
        assert cost == 18.0

    def test_calculate_cost_haiku(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """Haikuのコスト計算"""
        cost = provider._calculate_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        # input: 0.8, output: 4.0 → 4.8
        assert cost == pytest.approx(4.8)

    def test_calculate_cost_unknown_model(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """未知モデルはデフォルトSonnet料金"""
        cost = provider._calculate_cost("unknown-model", 1_000_000, 1_000_000)
        assert cost == 18.0

    async def test_generate(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """テキスト生成"""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_content = MagicMock()
        mock_content.text = "生成テキスト"
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(return_value=mock_response)

        result = await provider.generate("テストプロンプト")

        assert isinstance(result, LLMResponse)
        assert result.content == "生成テキスト"
        assert result.provider == "anthropic"
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.total_tokens == 150
        assert result.metadata["stop_reason"] == "end_turn"

    async def test_generate_with_system_prompt(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """システムプロンプト付き生成"""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 30
        mock_content = MagicMock()
        mock_content.text = "応答"
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(return_value=mock_response)

        result = await provider.generate("プロンプト", system_prompt="システム")

        assert result.content == "応答"
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["system"] == "システム"

    async def test_generate_api_error(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """APIエラー時に例外を伝播"""
        import anthropic

        provider._client.messages.create = AsyncMock(
            side_effect=anthropic.APIError(message="rate limit", request=MagicMock(), body=None)
        )

        with pytest.raises(anthropic.APIError):
            await provider.generate("テスト")

    async def test_generate_structured(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """構造化データ生成"""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 80
        mock_response.usage.output_tokens = 40
        mock_content = MagicMock()
        mock_content.text = '{"key": "value"}'
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(return_value=mock_response)

        result = await provider.generate_structured(
            "テスト", response_schema={"type": "object"}
        )

        assert result.content == '{"key": "value"}'
        call_kwargs = provider._client.messages.create.call_args
        assert "スキーマ" in call_kwargs.kwargs["system"]

    async def test_generate_fast(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """Haikuモデルで高速生成"""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 20
        mock_response.usage.output_tokens = 10
        mock_content = MagicMock()
        mock_content.text = "高速応答"
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(return_value=mock_response)

        result = await provider.generate_fast("テスト")

        assert result.content == "高速応答"
        call_kwargs = provider._client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"

    async def test_health_check_success(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """ヘルスチェック成功"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        result = await provider.health_check()
        assert result is True

    async def test_health_check_failure(self, provider: "AnthropicProvider") -> None:  # noqa: F821
        """ヘルスチェック失敗"""
        provider._client.messages.create = AsyncMock(side_effect=Exception("connection error"))

        result = await provider.health_check()
        assert result is False
