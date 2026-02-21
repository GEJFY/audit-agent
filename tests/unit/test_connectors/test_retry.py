"""コネクタリトライ + サーキットブレーカー テスト"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.connectors.base import CircuitBreaker, CircuitBreakerOpenError


@pytest.mark.unit
class TestCircuitBreaker:
    """CircuitBreaker 単体テスト"""

    def test_initial_state_closed(self) -> None:
        """初期状態はクローズ"""
        cb = CircuitBreaker()
        assert cb.is_open is False

    def test_record_success_resets(self) -> None:
        """成功でカウンタリセット"""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.is_open is False

    def test_opens_after_threshold(self) -> None:
        """閾値到達でオープン"""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_cooldown_resets(self) -> None:
        """クールダウン経過でハーフオープンに遷移"""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True
        time.sleep(0.02)
        assert cb.is_open is False
        assert cb._failure_count == 0

    def test_manual_reset(self) -> None:
        """手動リセット"""
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True
        cb.reset()
        assert cb.is_open is False
        assert cb._failure_count == 0


@pytest.mark.unit
class TestCircuitBreakerDecorator:
    """with_circuit_breaker デコレータテスト"""

    @pytest.mark.asyncio
    async def test_success_records(self) -> None:
        """正常時はcircuit_breaker.record_success()"""
        from src.connectors.sap import SAPConnector

        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="",
            )
            conn = SAPConnector()

        conn._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"d": {"results": []}}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        await conn.search("test")
        assert conn.circuit_breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_raises(self) -> None:
        """サーキットオープン時はCircuitBreakerOpenErrorを送出"""
        from src.connectors.sap import SAPConnector

        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="",
            )
            conn = SAPConnector()

        conn._client = AsyncMock()
        # サーキットブレーカーを手動オープン
        conn.circuit_breaker._is_open = True
        conn.circuit_breaker._last_failure_time = time.monotonic()

        with pytest.raises(CircuitBreakerOpenError):
            await conn.search("test")


@pytest.mark.unit
class TestConnectorRetry:
    """connector_retry テスト（tenacity統合）"""

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self) -> None:
        """httpx.ConnectError で最大3回リトライ"""
        from src.connectors.sharepoint import SharePointConnector

        with patch("src.connectors.sharepoint.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="tenant",
                azure_client_id="client",
                azure_client_secret="secret",
            )
            conn = SharePointConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        conn._client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused"),
        )

        # 3回リトライ後に例外
        with pytest.raises(httpx.ConnectError):
            await conn.search("test")

        # ConnectError → リトライ3回（初回含む）
        assert conn._client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """ReadTimeout で最大3回リトライ"""
        from src.connectors.email import EmailConnector

        with patch("src.connectors.email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="tenant",
                azure_client_id="client",
                azure_client_secret="secret",
            )
            conn = EmailConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        conn._client.get = AsyncMock(
            side_effect=httpx.ReadTimeout("Read timed out"),
        )

        with pytest.raises(httpx.ReadTimeout):
            await conn.search("audit report")

        assert conn._client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_http_status_error(self) -> None:
        """HTTPStatusError (400) はリトライ対象外"""
        from src.connectors.box import BoxConnector

        with patch("src.connectors.box.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                box_client_id="client",
                box_client_secret="secret",
                box_enterprise_id="enterprise",
            )
            conn = BoxConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response,
        )
        conn._client.get = AsyncMock(return_value=mock_response)

        # HTTPStatusErrorはリトライされずBox内部でキャッチ → []返却
        results = await conn.search("test")
        assert results == []
        assert conn._client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure(self) -> None:
        """リトライ失敗後にサーキットブレーカーが記録"""
        from src.connectors.sap import SAPConnector

        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="",
            )
            conn = SAPConnector()

        conn._client = AsyncMock()
        conn._client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused"),
        )

        with pytest.raises(httpx.ConnectError):
            await conn.search("test")

        # 失敗がサーキットブレーカーに記録される
        assert conn.circuit_breaker._failure_count > 0


@pytest.mark.unit
class TestHealthCheckLogging:
    """health_check ログ改善テスト"""

    @pytest.mark.asyncio
    async def test_sap_health_check_logs_error(self) -> None:
        """SAP health_check 失敗時にログ出力"""
        from src.connectors.sap import SAPConnector

        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="",
            )
            conn = SAPConnector()

        conn._client = AsyncMock()
        conn._client.get = AsyncMock(side_effect=TimeoutError("timeout"))

        with patch("src.connectors.sap.logger") as mock_logger:
            result = await conn.health_check()

        assert result is False
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_sharepoint_health_check_logs_error(self) -> None:
        """SharePoint health_check 失敗時にログ出力"""
        from src.connectors.sharepoint import SharePointConnector

        with patch("src.connectors.sharepoint.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="tenant",
                azure_client_id="client",
                azure_client_secret="secret",
            )
            conn = SharePointConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        conn._client.get = AsyncMock(side_effect=ConnectionError("refused"))

        with patch("src.connectors.sharepoint.logger") as mock_logger:
            result = await conn.health_check()

        assert result is False
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_health_check_logs_error(self) -> None:
        """Email health_check 失敗時にログ出力"""
        from src.connectors.email import EmailConnector

        with patch("src.connectors.email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="tenant",
                azure_client_id="client",
                azure_client_secret="secret",
            )
            conn = EmailConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        conn._client.get = AsyncMock(side_effect=TimeoutError("timeout"))

        with patch("src.connectors.email.logger") as mock_logger:
            result = await conn.health_check()

        assert result is False
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_box_health_check_logs_error(self) -> None:
        """Box health_check 失敗時にログ出力"""
        from src.connectors.box import BoxConnector

        with patch("src.connectors.box.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                box_client_id="client",
                box_client_secret="secret",
                box_enterprise_id="enterprise",
            )
            conn = BoxConnector()

        conn._access_token = "token"
        conn._client = AsyncMock()
        conn._client.get = AsyncMock(side_effect=OSError("Network down"))

        with patch("src.connectors.box.logger") as mock_logger:
            result = await conn.health_check()

        assert result is False
        mock_logger.warning.assert_called_once()
