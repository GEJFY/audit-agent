"""通知エンドポイント テスト"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.fixture
def notif_app():
    """通知ルート用テストアプリ"""
    return create_app()


@pytest.fixture
async def notif_client(notif_app):
    """通知ルート用テストクライアント"""
    transport = ASGITransport(app=notif_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.unit
class TestListProviders:
    """GET /notifications/providers テスト"""

    async def test_list_providers_empty(self, notif_client: AsyncClient) -> None:
        """プロバイダ未登録時"""
        resp = await notif_client.get("/api/v1/notifications/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "count" in data
        assert isinstance(data["providers"], list)


@pytest.mark.unit
class TestSendNotification:
    """POST /notifications/send テスト"""

    async def test_send_no_providers(self, notif_client: AsyncClient) -> None:
        """プロバイダ未登録で送信 → 空の結果"""
        resp = await notif_client.post(
            "/api/v1/notifications/send",
            json={
                "title": "テスト通知",
                "body": "テスト本文",
                "priority": "medium",
                "tenant_id": "t-001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 0
        assert data["failure_count"] == 0

    async def test_send_invalid_priority(self, notif_client: AsyncClient) -> None:
        """無効な優先度 → mediumにフォールバック"""
        resp = await notif_client.post(
            "/api/v1/notifications/send",
            json={
                "title": "テスト",
                "body": "本文",
                "priority": "invalid_priority",
            },
        )
        assert resp.status_code == 200

    async def test_send_with_action_url(self, notif_client: AsyncClient) -> None:
        """アクションURL付き送信"""
        resp = await notif_client.post(
            "/api/v1/notifications/send",
            json={
                "title": "承認依頼",
                "body": "承認をお願いします",
                "priority": "high",
                "action_url": "https://example.com/approve/123",
            },
        )
        assert resp.status_code == 200


@pytest.mark.unit
class TestEscalation:
    """POST /notifications/escalation テスト"""

    async def test_send_escalation(self, notif_client: AsyncClient) -> None:
        """エスカレーション通知送信"""
        resp = await notif_client.post(
            "/api/v1/notifications/escalation",
            json={
                "tenant_id": "t-001",
                "title": "重要な検出事項",
                "body": "即座の対応が必要です",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sent" in data


@pytest.mark.unit
class TestRiskAlert:
    """POST /notifications/risk-alert テスト"""

    async def test_send_risk_alert(self, notif_client: AsyncClient) -> None:
        """リスクアラート送信"""
        resp = await notif_client.post(
            "/api/v1/notifications/risk-alert",
            json={
                "tenant_id": "t-001",
                "title": "リスクスコア急上昇",
                "body": "財務リスクスコアが閾値を超えました",
                "priority": "critical",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sent" in data

    async def test_send_risk_alert_default_priority(self, notif_client: AsyncClient) -> None:
        """デフォルト優先度（high）でアラート送信"""
        resp = await notif_client.post(
            "/api/v1/notifications/risk-alert",
            json={
                "tenant_id": "t-001",
                "title": "テスト",
                "body": "テスト",
            },
        )
        assert resp.status_code == 200


@pytest.mark.unit
class TestProvidersHealth:
    """GET /notifications/health テスト"""

    async def test_health_no_providers(self, notif_client: AsyncClient) -> None:
        """プロバイダ未登録時のヘルスチェック"""
        resp = await notif_client.get("/api/v1/notifications/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["providers"] == {}

    @patch(
        "src.api.routes.notifications._dispatcher.health_check_all",
        new_callable=AsyncMock,
    )
    async def test_health_with_providers(self, mock_health: AsyncMock, notif_client: AsyncClient) -> None:
        """プロバイダ登録時のヘルスチェック"""
        mock_health.return_value = {"slack": True, "teams": False}
        resp = await notif_client.get("/api/v1/notifications/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
