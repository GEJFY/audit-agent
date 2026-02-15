"""Teams通知プロバイダのテスト"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.notifications.base import NotificationMessage, NotificationPriority
from src.notifications.teams import TeamsProvider


@pytest.fixture
def teams_provider():
    return TeamsProvider(webhook_url="https://outlook.office.com/webhook/xxx")


@pytest.fixture
def empty_provider():
    return TeamsProvider(webhook_url="")


@pytest.fixture
def sample_message():
    return NotificationMessage(
        title="テスト通知",
        body="テスト本文です",
        priority=NotificationPriority.HIGH,
        tenant_id="tenant-001",
        source="escalation",
        action_url="https://app.example.com/approval/456",
    )


@pytest.fixture
def minimal_message():
    return NotificationMessage(
        title="シンプル通知",
        body="本文のみ",
    )


class TestTeamsProviderProperties:
    """プロバイダプロパティテスト"""

    def test_provider_name(self, teams_provider):
        assert teams_provider.provider_name == "teams"

    def test_webhook_url_stored(self, teams_provider):
        assert teams_provider._webhook_url == "https://outlook.office.com/webhook/xxx"


class TestTeamsBuildAdaptiveCard:
    """Adaptive Card構築テスト"""

    def test_card_envelope_structure(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        assert card["type"] == "message"
        assert len(card["attachments"]) == 1
        assert card["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"

    def test_adaptive_card_schema(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        content = card["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"
        assert content["version"] == "1.4"
        assert "$schema" in content

    def test_title_text_block(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        body = card["attachments"][0]["content"]["body"]
        title_block = body[0]
        assert title_block["type"] == "TextBlock"
        assert title_block["text"] == "テスト通知"
        assert title_block["weight"] == "Bolder"

    def test_body_text_block(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        body = card["attachments"][0]["content"]["body"]
        body_block = body[1]
        assert body_block["text"] == "テスト本文です"
        assert body_block["wrap"] is True

    def test_fact_set_with_metadata(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        body = card["attachments"][0]["content"]["body"]
        fact_set = body[2]
        assert fact_set["type"] == "FactSet"
        assert len(fact_set["facts"]) == 3  # source, tenant_id, priority

    def test_fact_set_values(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        body = card["attachments"][0]["content"]["body"]
        facts = body[2]["facts"]
        titles = [f["title"] for f in facts]
        assert "種別" in titles
        assert "テナント" in titles
        assert "優先度" in titles

    def test_action_url_present(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        content = card["attachments"][0]["content"]
        assert "actions" in content
        action = content["actions"][0]
        assert action["type"] == "Action.OpenUrl"
        assert action["url"] == "https://app.example.com/approval/456"

    def test_no_action_without_url(self, teams_provider, minimal_message):
        card = teams_provider._build_adaptive_card(minimal_message)
        content = card["attachments"][0]["content"]
        assert "actions" not in content

    def test_priority_color_high(self, teams_provider, sample_message):
        card = teams_provider._build_adaptive_card(sample_message)
        body = card["attachments"][0]["content"]["body"]
        assert body[0]["color"] == "attention"

    def test_priority_color_low(self, teams_provider):
        msg = NotificationMessage(title="情報", body="低優先度", priority=NotificationPriority.LOW)
        card = teams_provider._build_adaptive_card(msg)
        body = card["attachments"][0]["content"]["body"]
        assert body[0]["color"] == "good"

    def test_priority_color_medium(self, teams_provider):
        msg = NotificationMessage(title="注意", body="中優先度", priority=NotificationPriority.MEDIUM)
        card = teams_provider._build_adaptive_card(msg)
        body = card["attachments"][0]["content"]["body"]
        assert body[0]["color"] == "warning"


class TestTeamsSend:
    """送信テスト"""

    @pytest.mark.asyncio
    async def test_send_success(self, teams_provider, sample_message):
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch.object(httpx.AsyncClient, "post", return_value=mock_response) as mock_post:
            result = await teams_provider.send(sample_message)
            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_empty_webhook_returns_false(self, empty_provider, sample_message):
        result = await empty_provider.send(sample_message)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_http_error_returns_false(self, teams_provider, sample_message):
        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.HTTPStatusError("error", request=None, response=None),
        ):
            result = await teams_provider.send(sample_message)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error_returns_false(self, teams_provider, sample_message):
        with patch.object(
            httpx.AsyncClient,
            "post",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            result = await teams_provider.send(sample_message)
            assert result is False


class TestTeamsHealthCheck:
    """ヘルスチェックテスト"""

    @pytest.mark.asyncio
    async def test_health_check_with_url(self, teams_provider):
        assert await teams_provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_without_url(self, empty_provider):
        assert await empty_provider.health_check() is False


class TestTeamsClose:
    """クライアント終了テスト"""

    @pytest.mark.asyncio
    async def test_close_without_client(self, teams_provider):
        await teams_provider.close()
        assert teams_provider._client is None

    @pytest.mark.asyncio
    async def test_close_with_client(self, teams_provider):
        teams_provider._client = httpx.AsyncClient()
        await teams_provider.close()
        assert teams_provider._client is None
