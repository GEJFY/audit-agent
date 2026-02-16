"""Azure OpenAIプロバイダーテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm_gateway.providers.base import LLMResponse


@pytest.mark.unit
class TestAzureOpenAIProvider:
    """AzureOpenAIProviderのテスト"""

    @pytest.fixture
    def provider(self) -> "AzureOpenAIProvider":  # noqa: F821
        """モック設定でプロバイダーを作成"""
        with patch("src.llm_gateway.providers.azure_openai.get_settings") as mock_settings:
            settings = MagicMock()
            settings.azure_openai_api_key = "test-api-key"
            settings.azure_openai_endpoint = "https://test.openai.azure.com"
            settings.azure_openai_api_version = "2024-02-01"
            settings.azure_openai_deployment = "gpt-4o"
            mock_settings.return_value = settings

            from src.llm_gateway.providers.azure_openai import AzureOpenAIProvider

            return AzureOpenAIProvider()

    def test_provider_name(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """プロバイダー名"""
        assert provider.provider_name == "azure_openai"

    def test_client_lazy_init(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """クライアントは遅延初期化"""
        assert provider._client is None

    async def test_generate(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """テキスト生成"""
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Azure応答"
        mock_choice.finish_reason = "stop"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 40
        mock_usage.total_tokens = 120
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate("テストプロンプト")

        assert isinstance(result, LLMResponse)
        assert result.content == "Azure応答"
        assert result.provider == "azure_openai"
        assert result.input_tokens == 80
        assert result.output_tokens == 40
        assert result.total_tokens == 120

    async def test_generate_with_system_prompt(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """システムプロンプト付き生成"""
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "応答"
        mock_choice.finish_reason = "stop"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 70
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        await provider.generate("テスト", system_prompt="システム指示")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "システム指示"

    async def test_generate_api_error(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """APIエラー時に例外を伝播"""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("Azure API error"))
        provider._client = mock_client

        with pytest.raises(RuntimeError, match="Azure API error"):
            await provider.generate("テスト")

    async def test_generate_no_usage(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """usage=Noneの場合"""
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "応答"
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate("テスト")
        assert result.input_tokens == 0
        assert result.output_tokens == 0

    async def test_generate_structured(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """構造化データ生成"""
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": true}'
        mock_choice.finish_reason = "stop"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 60
        mock_usage.completion_tokens = 30
        mock_usage.total_tokens = 90
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_structured("テスト", response_schema={"type": "object"})
        assert result.content == '{"result": true}'

    async def test_health_check_no_credentials(self) -> None:
        """認証情報なしのヘルスチェック"""
        with patch("src.llm_gateway.providers.azure_openai.get_settings") as mock_settings:
            settings = MagicMock()
            settings.azure_openai_api_key = ""
            settings.azure_openai_endpoint = ""
            settings.azure_openai_api_version = "2024-02-01"
            settings.azure_openai_deployment = "gpt-4o"
            mock_settings.return_value = settings

            from src.llm_gateway.providers.azure_openai import AzureOpenAIProvider

            p = AzureOpenAIProvider()
            result = await p.health_check()
            assert result is False

    async def test_health_check_success(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """ヘルスチェック成功"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.health_check()
        assert result is True

    async def test_health_check_failure(self, provider: "AzureOpenAIProvider") -> None:  # noqa: F821
        """ヘルスチェック失敗"""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("error"))
        provider._client = mock_client

        result = await provider.health_check()
        assert result is False
