"""通知ディスパッチャー統合テスト

Slack/TeamsプロバイダとDispatcherの統合動作を確認。
実際のWebhook送信は行わず、プロバイダ登録〜ディスパッチフローを検証。
"""

import pytest

from src.notifications.base import NotificationMessage, NotificationPriority
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.slack import SlackProvider
from src.notifications.teams import TeamsProvider


@pytest.mark.integration
class TestNotificationDispatcherIntegration:
    """Dispatcher + Provider統合テスト"""

    async def test_register_and_list_providers(self) -> None:
        """プロバイダ登録と一覧取得"""
        dispatcher = NotificationDispatcher()
        slack = SlackProvider(webhook_url="https://hooks.slack.com/test")
        teams = TeamsProvider(webhook_url="https://teams.webhook.test")

        dispatcher.register_provider(slack)
        dispatcher.register_provider(teams)

        providers = dispatcher.list_providers()
        assert "slack" in providers
        assert "teams" in providers
        assert len(providers) == 2

    async def test_health_check_all(self) -> None:
        """全プロバイダヘルスチェック"""
        dispatcher = NotificationDispatcher()
        slack = SlackProvider(webhook_url="https://hooks.slack.com/test")
        teams = TeamsProvider(webhook_url="")  # 空 = unhealthy

        dispatcher.register_provider(slack)
        dispatcher.register_provider(teams)

        results = await dispatcher.health_check_all()
        assert results["slack"] is True
        assert results["teams"] is False

    async def test_dispatch_to_unknown_provider(self) -> None:
        """未登録プロバイダへのディスパッチ"""
        dispatcher = NotificationDispatcher()
        message = NotificationMessage(
            title="テスト",
            body="テスト本文",
            priority=NotificationPriority.MEDIUM,
        )

        results = await dispatcher.dispatch(message, provider_names=["unknown"])
        assert results["unknown"] is False

    async def test_tenant_channel_setting(self) -> None:
        """テナント別チャンネル設定"""
        dispatcher = NotificationDispatcher()
        slack = SlackProvider(webhook_url="https://hooks.slack.com/test")
        dispatcher.register_provider(slack)

        dispatcher.set_tenant_channel("t-001", "slack", "#audit-alerts")

        # チャンネル設定が保持されていることを確認
        assert "t-001" in dispatcher._tenant_channels
        assert dispatcher._tenant_channels["t-001"]["slack"] == "#audit-alerts"

    async def test_dispatch_escalation(self) -> None:
        """エスカレーション通知ディスパッチ"""
        dispatcher = NotificationDispatcher()
        # プロバイダ未登録のまま — 結果は空辞書
        results = await dispatcher.dispatch_escalation(
            tenant_id="t-001",
            title="エスカレーション",
            body="緊急対応が必要です",
        )
        assert isinstance(results, dict)

    async def test_dispatch_risk_alert(self) -> None:
        """リスクアラートディスパッチ"""
        dispatcher = NotificationDispatcher()
        results = await dispatcher.dispatch_risk_alert(
            tenant_id="t-001",
            title="リスク急上昇",
            body="スコアが閾値を超えました",
            priority=NotificationPriority.CRITICAL,
        )
        assert isinstance(results, dict)

    async def test_dispatch_approval_request(self) -> None:
        """承認依頼ディスパッチ"""
        dispatcher = NotificationDispatcher()
        results = await dispatcher.dispatch_approval_request(
            tenant_id="t-001",
            title="承認依頼",
            body="レポートの承認をお願いします",
            action_url="https://example.com/approve/123",
        )
        assert isinstance(results, dict)


@pytest.mark.integration
class TestSlackProviderIntegration:
    """SlackProvider統合テスト"""

    async def test_build_payload(self) -> None:
        """Block Kit ペイロード構築"""
        slack = SlackProvider(webhook_url="https://test.webhook")
        message = NotificationMessage(
            title="テスト通知",
            body="テスト本文",
            priority=NotificationPriority.HIGH,
            tenant_id="t-001",
            source="risk_alert",
            action_url="https://example.com/action",
        )

        payload = slack._build_payload(message)
        assert "blocks" in payload
        assert len(payload["blocks"]) >= 2  # header + section
        assert "attachments" in payload

    async def test_health_check_with_url(self) -> None:
        """Webhook URL設定済み → healthy"""
        slack = SlackProvider(webhook_url="https://test.webhook")
        assert await slack.health_check() is True

    async def test_health_check_without_url(self) -> None:
        """Webhook URL未設定 → unhealthy"""
        slack = SlackProvider(webhook_url="")
        assert await slack.health_check() is False


@pytest.mark.integration
class TestTeamsProviderIntegration:
    """TeamsProvider統合テスト"""

    async def test_build_adaptive_card(self) -> None:
        """Adaptive Card構築"""
        teams = TeamsProvider(webhook_url="https://test.webhook")
        message = NotificationMessage(
            title="テスト通知",
            body="テスト本文",
            priority=NotificationPriority.CRITICAL,
            source="escalation",
            action_url="https://example.com/action",
        )

        payload = teams._build_adaptive_card(message)
        assert payload["type"] == "message"
        assert len(payload["attachments"]) == 1
        content = payload["attachments"][0]["content"]
        assert content["type"] == "AdaptiveCard"
        assert "actions" in content
