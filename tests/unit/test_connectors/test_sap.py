"""SAP コネクタ ユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.connectors.sap import SAPConnector


def _create_connector() -> SAPConnector:
    """テスト用SAPコネクタ生成"""
    with patch("src.connectors.sap.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            sap_base_url="https://sap.example.com",
            sap_username="user",
            sap_password="pass",
            sap_client_id="",
        )
        return SAPConnector()


def _connected_connector() -> SAPConnector:
    """接続済みSAPコネクタ"""
    conn = _create_connector()
    conn._client = AsyncMock()
    conn._access_token = None
    return conn


def _oauth_connector() -> SAPConnector:
    """OAuth接続済みSAPコネクタ"""
    conn = _create_connector()
    conn._client_id = "test_client"
    conn._client = AsyncMock()
    conn._access_token = "test_token"
    return conn


@pytest.mark.unit
class TestSAPConnector:
    """SAPConnector テスト"""

    def test_connector_name(self) -> None:
        conn = _create_connector()
        assert conn.connector_name == "sap"

    @pytest.mark.asyncio
    async def test_connect_missing_settings(self) -> None:
        """接続先URLが未設定の場合は接続失敗"""
        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="",
                sap_username="",
                sap_password="",
                sap_client_id="",
            )
            conn = SAPConnector()
        result = await conn.connect()
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_basic_auth(self) -> None:
        """Basic Auth接続成功"""
        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="",
            )
            conn = SAPConnector()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await conn.connect()

        assert result is True

    @pytest.mark.asyncio
    async def test_connect_oauth(self) -> None:
        """OAuth接続成功"""
        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="https://sap.example.com",
                sap_username="user",
                sap_password="pass",
                sap_client_id="client123",
            )
            conn = SAPConnector()

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new_token"}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await conn.connect()

        assert result is True
        assert conn._access_token == "new_token"

    @pytest.mark.asyncio
    async def test_search_fi_module(self) -> None:
        """FIモジュール検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "d": {
                "results": [
                    {
                        "CompanyCode": "1000",
                        "AccountingDocument": "DOC001",
                        "AmountInCompanyCodeCurrency": 50000,
                        "__metadata": {"uri": "internal"},
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("CompanyCode eq '1000'", module="fi")
        assert len(results) == 1
        assert results[0]["CompanyCode"] == "1000"
        assert results[0]["source"] == "sap"
        assert results[0]["module"] == "fi"
        # __metadata が除去されていることを確認
        assert "__metadata" not in results[0]

    @pytest.mark.asyncio
    async def test_search_mm_module(self) -> None:
        """MMモジュール検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"d": {"results": []}}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("", module="mm")
        assert results == []

        # URLにMMサービスが使われていることを確認
        call_args = conn._client.get.call_args
        url = call_args.args[0]
        assert "API_PURCHASEORDER_PROCESS_SRV" in url

    @pytest.mark.asyncio
    async def test_search_with_custom_service(self) -> None:
        """カスタムサービス指定検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"d": {"results": []}}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        await conn.search(
            "",
            service="CUSTOM_SRV",
            entity_set="CustomEntity",
            top=50,
        )

        call_args = conn._client.get.call_args
        url = call_args.args[0]
        assert "CUSTOM_SRV" in url
        assert "CustomEntity" in url

    @pytest.mark.asyncio
    async def test_search_not_connected(self) -> None:
        """未接続時は空リスト（connect失敗）"""
        with patch("src.connectors.sap.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sap_base_url="",
                sap_username="",
                sap_password="",
                sap_client_id="",
            )
            conn = SAPConnector()
        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self) -> None:
        """HTTPエラー時は空リスト"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_401_retry(self) -> None:
        """401時にトークン再取得してリトライ"""
        conn = _oauth_connector()

        # 1回目: 401エラー
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=error_response,
        )

        # 2回目: 成功（connect → search）
        ok_response = MagicMock()
        ok_response.json.return_value = {"d": {"results": []}}
        ok_response.raise_for_status = MagicMock()

        # connect時のOAuthレスポンス
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "refreshed_token"}
        token_response.raise_for_status = MagicMock()

        conn._client.get = AsyncMock(side_effect=[error_response, ok_response])
        conn._client.post = AsyncMock(return_value=token_response)

        # connectがネットワークアクセスしないようモック
        async def mock_connect() -> bool:
            conn._access_token = "refreshed_token"
            return True

        conn.connect = mock_connect  # type: ignore[assignment]

        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_journal_entries(self) -> None:
        """仕訳データ取得"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "d": {
                "results": [
                    {
                        "CompanyCode": "1000",
                        "FiscalYear": "2025",
                        "AccountingDocument": "DOC001",
                        "PostingDate": "/Date(1735689600000)/",
                        "GLAccount": "400000",
                        "AmountInCompanyCodeCurrency": 100000,
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.get_journal_entries(
            company_code="1000",
            fiscal_year=2025,
            posting_date_from="2025-01-01",
            posting_date_to="2025-12-31",
        )

        assert len(results) == 1
        assert results[0]["CompanyCode"] == "1000"
        # フィルタにCompanyCode, FiscalYear, PostingDate範囲が含まれることを確認
        call_kwargs = conn._client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "CompanyCode eq '1000'" in params["$filter"]
        assert "FiscalYear eq '2025'" in params["$filter"]

    @pytest.mark.asyncio
    async def test_get_purchase_orders(self) -> None:
        """発注データ取得"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"d": {"results": []}}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.get_purchase_orders(company_code="1000")
        assert results == []

    @pytest.mark.asyncio
    async def test_health_check_connected(self) -> None:
        """ヘルスチェック — 接続中"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.status_code = 200
        conn._client.get = AsyncMock(return_value=mock_response)

        assert await conn.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self) -> None:
        """ヘルスチェック — 未接続"""
        conn = _create_connector()
        assert await conn.health_check() is False

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """切断"""
        conn = _connected_connector()
        await conn.disconnect()
        assert conn._client is None
        assert conn._access_token is None

    def test_get_headers_with_token(self) -> None:
        """Bearerトークン付きヘッダー"""
        conn = _oauth_connector()
        headers = conn._get_headers()
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["sap-client"] == "100"

    def test_get_headers_without_token(self) -> None:
        """トークンなしヘッダー"""
        conn = _connected_connector()
        headers = conn._get_headers()
        assert "Authorization" not in headers

    def test_get_auth_basic(self) -> None:
        """Basic Auth情報"""
        conn = _connected_connector()
        auth = conn._get_auth()
        assert auth == ("user", "pass")

    def test_get_auth_bearer(self) -> None:
        """Bearer使用時はauth=None"""
        conn = _oauth_connector()
        auth = conn._get_auth()
        assert auth is None
