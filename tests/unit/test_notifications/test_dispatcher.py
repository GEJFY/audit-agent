"""通知ディスパッチャーのテスト"""

import pytest

from src.notifications.base import BaseNotificationProvider, NotificationMessage, NotificationPriority
from src.notifications.dispatcher import NotificationDispatcher


class FakeProvider(BaseNotificationProvider):
    """テスト用のフェイクプロバイダ"""

    def __init__(self, name: str = "fake", succeed: bool = True) -> None:
        self._name = name
        self._succeed = succeed
        self.sent_messages: list[tuple[NotificationMessage, str]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    async def send(self, message: NotificationMessage, channel: str) -> bool:
        self.sent_messages.append((message, channel))
        return self._succeed

    async def health_check(self) -> bool:
        return self._succeed


class ErrorProvider(BaseNotificationProvider):
    """送信時にエラーを発生させるプロバイダ"""

    @property
    def provider_name(self) -> str:
        return "error"

    async def send(self, message: NotificationMessage, channel: str) -> bool:
        raise RuntimeError("送信エラー")

    async def health_check(self) -> bool:
        raise RuntimeError("ヘルスチェックエラー")


@pytest.fixture
def dispatcher():
    return NotificationDispatcher()


@pytest.fixture
def slack_fake():
    return FakeProvider(name="slack")


@pytest.fixture
def teams_fake():
    return FakeProvider(name="teams")


@pytest.fixture
def failing_provider():
    return FakeProvider(name="failing", succeed=False)


@pytest.fixture
def error_provider():
    return ErrorProvider()


@pytest.fixture
def sample_message():
    return NotificationMessage(
        title="テスト通知",
        body="テスト本文",
        priority=NotificationPriority.HIGH,
        tenant_id="tenant-001",
        source="risk_alert",
    )


class TestRegisterProvider:
    """プロバイダ登録テスト"""

    def test_register_single_provider(self, dispatcher, slack_fake):
        dispatcher.register_provider(slack_fake)
        assert "slack" in dispatcher.list_providers()

    def test_register_multiple_providers(self, dispatcher, slack_fake, teams_fake):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(teams_fake)
        assert sorted(dispatcher.list_providers()) == ["slack", "teams"]

    def test_list_providers_empty(self, dispatcher):
        assert dispatcher.list_providers() == []


class TestTenantChannel:
    """テナントチャンネル設定テスト"""

    def test_set_tenant_channel(self, dispatcher):
        dispatcher.set_tenant_channel("tenant-001", "slack", "#audit-alerts")
        assert dispatcher._tenant_channels["tenant-001"]["slack"] == "#audit-alerts"

    def test_set_multiple_channels(self, dispatcher):
        dispatcher.set_tenant_channel("tenant-001", "slack", "#general")
        dispatcher.set_tenant_channel("tenant-001", "teams", "channel-123")
        assert len(dispatcher._tenant_channels["tenant-001"]) == 2


class TestDispatch:
    """通知振り分けテスト"""

    @pytest.mark.asyncio
    async def test_dispatch_to_all_providers(self, dispatcher, slack_fake, teams_fake, sample_message):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(teams_fake)
        results = await dispatcher.dispatch(sample_message)
        assert results == {"slack": True, "teams": True}
        assert len(slack_fake.sent_messages) == 1
        assert len(teams_fake.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_dispatch_to_specific_provider(self, dispatcher, slack_fake, teams_fake, sample_message):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(teams_fake)
        results = await dispatcher.dispatch(sample_message, provider_names=["slack"])
        assert results == {"slack": True}
        assert len(teams_fake.sent_messages) == 0

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_provider(self, dispatcher, sample_message):
        results = await dispatcher.dispatch(sample_message, provider_names=["unknown"])
        assert results == {"unknown": False}

    @pytest.mark.asyncio
    async def test_dispatch_with_tenant_channel(self, dispatcher, slack_fake, sample_message):
        dispatcher.register_provider(slack_fake)
        dispatcher.set_tenant_channel("tenant-001", "slack", "#audit-alerts")
        await dispatcher.dispatch(sample_message)
        _, channel = slack_fake.sent_messages[0]
        assert channel == "#audit-alerts"

    @pytest.mark.asyncio
    async def test_dispatch_no_tenant_channel(self, dispatcher, slack_fake, sample_message):
        dispatcher.register_provider(slack_fake)
        await dispatcher.dispatch(sample_message)
        _, channel = slack_fake.sent_messages[0]
        assert channel == ""

    @pytest.mark.asyncio
    async def test_dispatch_failing_provider(self, dispatcher, failing_provider, sample_message):
        dispatcher.register_provider(failing_provider)
        results = await dispatcher.dispatch(sample_message)
        assert results == {"failing": False}

    @pytest.mark.asyncio
    async def test_dispatch_error_provider(self, dispatcher, error_provider, sample_message):
        dispatcher.register_provider(error_provider)
        results = await dispatcher.dispatch(sample_message)
        assert results == {"error": False}

    @pytest.mark.asyncio
    async def test_dispatch_mixed_results(self, dispatcher, slack_fake, failing_provider, sample_message):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(failing_provider)
        results = await dispatcher.dispatch(sample_message)
        assert results["slack"] is True
        assert results["failing"] is False


class TestConvenienceMethods:
    """ヘルパーメソッドテスト"""

    @pytest.mark.asyncio
    async def test_dispatch_escalation(self, dispatcher, slack_fake):
        dispatcher.register_provider(slack_fake)
        results = await dispatcher.dispatch_escalation(
            tenant_id="tenant-001",
            title="エスカレーション",
            body="重要な問題です",
            action_url="https://app.example.com/issue/1",
        )
        assert results == {"slack": True}
        msg, _ = slack_fake.sent_messages[0]
        assert msg.priority == NotificationPriority.HIGH
        assert msg.source == "escalation"
        assert msg.action_url == "https://app.example.com/issue/1"

    @pytest.mark.asyncio
    async def test_dispatch_approval_request(self, dispatcher, slack_fake):
        dispatcher.register_provider(slack_fake)
        results = await dispatcher.dispatch_approval_request(
            tenant_id="tenant-001",
            title="承認依頼",
            body="承認をお願いします",
        )
        assert results == {"slack": True}
        msg, _ = slack_fake.sent_messages[0]
        assert msg.priority == NotificationPriority.MEDIUM
        assert msg.source == "approval_request"

    @pytest.mark.asyncio
    async def test_dispatch_risk_alert(self, dispatcher, slack_fake):
        dispatcher.register_provider(slack_fake)
        results = await dispatcher.dispatch_risk_alert(
            tenant_id="tenant-001",
            title="リスクアラート",
            body="異常検知",
            priority=NotificationPriority.CRITICAL,
        )
        assert results == {"slack": True}
        msg, _ = slack_fake.sent_messages[0]
        assert msg.priority == NotificationPriority.CRITICAL
        assert msg.source == "risk_alert"

    @pytest.mark.asyncio
    async def test_dispatch_risk_alert_default_priority(self, dispatcher, slack_fake):
        dispatcher.register_provider(slack_fake)
        await dispatcher.dispatch_risk_alert(
            tenant_id="tenant-001",
            title="リスクアラート",
            body="異常検知",
        )
        msg, _ = slack_fake.sent_messages[0]
        assert msg.priority == NotificationPriority.HIGH


class TestHealthCheck:
    """ヘルスチェックテスト"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, dispatcher, slack_fake, teams_fake):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(teams_fake)
        results = await dispatcher.health_check_all()
        assert results == {"slack": True, "teams": True}

    @pytest.mark.asyncio
    async def test_health_check_with_error(self, dispatcher, slack_fake, error_provider):
        dispatcher.register_provider(slack_fake)
        dispatcher.register_provider(error_provider)
        results = await dispatcher.health_check_all()
        assert results["slack"] is True
        assert results["error"] is False

    @pytest.mark.asyncio
    async def test_health_check_empty(self, dispatcher):
        results = await dispatcher.health_check_all()
        assert results == {}
