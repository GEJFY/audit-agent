"""Slack通知プロバイダのテスト"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.notifications.base import NotificationMessage, NotificationPriority
from src.notifications.slack import SlackProvider


@pytest.fixture
def slack_provider():
    return SlackProvider(webhook_url="https://hooks.slack.com/services/T00/B00/xxx")


@pytest.fixture
def empty_provider():
    return SlackProvider(webhook_url="")


@pytest.fixture
def sample_message():
    return NotificationMessage(
        title="テスト通知",
        body="テスト本文です",
        priority=NotificationPriority.HIGH,
        tenant_id="tenant-001",
        source="risk_alert",
        action_url="https://app.example.com/finding/123",
    )


@pytest.fixture
def minimal_message():
    return NotificationMessage(
        title="シンプル通知",
        body="本文のみ",
    )


class TestSlackProviderProperties:
    """プロバイダプロパティテスト"""

    def test_provider_name(self, slack_provider):
        assert slack_provider.provider_name == "slack"

    def test_webhook_url_stored(self, slack_provider):
        assert slack_provider._webhook_url == "https://hooks.slack.com/services/T00/B00/xxx"


class TestSlackBuildPayload:
    """ペイロード構築テスト"""

    def test_basic_payload_structure(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        assert "blocks" in payload
        assert "attachments" in payload

    def test_header_block(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        header = payload["blocks"][0]
        assert header["type"] == "header"
        assert "テスト通知" in header["text"]["text"]

    def test_body_block(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        section = payload["blocks"][1]
        assert section["type"] == "section"
        assert section["text"]["text"] == "テスト本文です"

    def test_fields_with_source_and_tenant(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        fields_block = payload["blocks"][2]
        assert fields_block["type"] == "section"
        assert len(fields_block["fields"]) == 3  # source, tenant_id, priority

    def test_action_url_button(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        actions_block = payload["blocks"][3]
        assert actions_block["type"] == "actions"
        button = actions_block["elements"][0]
        assert button["url"] == "https://app.example.com/finding/123"
        assert button["style"] == "primary"

    def test_no_action_url(self, slack_provider, minimal_message):
        payload = slack_provider._build_payload(minimal_message)
        # アクションブロック無し（header + body のみ）
        for block in payload["blocks"]:
            assert block["type"] != "actions"

    def test_priority_emoji_high(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        header_text = payload["blocks"][0]["text"]["text"]
        assert ":exclamation:" in header_text

    def test_priority_emoji_critical(self, slack_provider):
        msg = NotificationMessage(title="緊急", body="緊急通知", priority=NotificationPriority.CRITICAL)
        payload = slack_provider._build_payload(msg)
        header_text = payload["blocks"][0]["text"]["text"]
        assert ":rotating_light:" in header_text

    def test_priority_color_mapping(self, slack_provider, sample_message):
        payload = slack_provider._build_payload(sample_message)
        color = payload["attachments"][0]["color"]
        assert color == "#ff6600"  # HIGH

    def test_low_priority_color(self, slack_provider):
        msg = NotificationMessage(title="情報", body="低優先度", priority=NotificationPriority.LOW)
        payload = slack_provider._build_payload(msg)
        assert payload["attachments"][0]["color"] == "#36a64f"

    def test_minimal_message_no_fields(self, slack_provider, minimal_message):
        """source/tenant未設定でもフィールドブロックは優先度のみ"""
        payload = slack_provider._build_payload(minimal_message)
        # header + body + fields(priorityのみ)
        assert len(payload["blocks"]) >= 2


class TestSlackSend:
    """送信テスト"""

    @pytest.mark.asyncio
    async def test_send_success(self, slack_provider, sample_message):
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch.object(httpx.AsyncClient, "post", return_value=mock_response) as mock_post:
            result = await slack_provider.send(sample_message)
            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_empty_webhook_returns_false(self, empty_provider, sample_message):
        result = await empty_provider.send(sample_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_http_error_returns_false(self, slack_provider, sample_message):
        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.HTTPStatusError("error", request=None, response=None),
        ):
            result = await slack_provider.send(sample_message)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error_returns_false(self, slack_provider, sample_message):
        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            result = await slack_provider.send(sample_message)
            assert result is False


class TestSlackHealthCheck:
    """ヘルスチェックテスト"""

    @pytest.mark.asyncio
    async def test_health_check_with_url(self, slack_provider):
        assert await slack_provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_without_url(self, empty_provider):
        assert await empty_provider.health_check() is False


class TestSlackClose:
    """クライアント終了テスト"""

    @pytest.mark.asyncio
    async def test_close_without_client(self, slack_provider):
        await slack_provider.close()
        assert slack_provider._client is None

    @pytest.mark.asyncio
    async def test_close_with_client(self, slack_provider):
        slack_provider._client = httpx.AsyncClient()
        await slack_provider.close()
        assert slack_provider._client is None
