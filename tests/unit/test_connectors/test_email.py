"""Email コネクタ ユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.connectors.email import EmailConnector


def _create_connector() -> EmailConnector:
    """テスト用Emailコネクタ生成"""
    with patch("src.connectors.email.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
        )
        return EmailConnector()


def _connected_connector() -> EmailConnector:
    """接続済みEmailコネクタ"""
    conn = _create_connector()
    conn._client = AsyncMock()
    conn._access_token = "test_token"
    return conn


@pytest.mark.unit
class TestEmailConnector:
    """EmailConnector テスト"""

    def test_connector_name(self) -> None:
        conn = _create_connector()
        assert conn.connector_name == "email"

    @pytest.mark.asyncio
    async def test_connect_missing_settings(self) -> None:
        """Azure AD設定不完全時は接続失敗"""
        with patch("src.connectors.email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="",
                azure_client_id="",
                azure_client_secret="",
            )
            conn = EmailConnector()
        result = await conn.connect()
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """OAuth接続成功"""
        conn = _create_connector()
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
    async def test_connect_failure(self) -> None:
        """接続エラー"""
        conn = _create_connector()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await conn.connect()

        assert result is False

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        """メール検索成功"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "msg-001",
                    "subject": "監査依頼: Q4決算",
                    "bodyPreview": "第4四半期の監査について...",
                    "from": {
                        "emailAddress": {
                            "name": "田中太郎",
                            "address": "tanaka@example.com",
                        }
                    },
                    "toRecipients": [{"emailAddress": {"address": "audit@example.com"}}],
                    "receivedDateTime": "2025-12-01T09:00:00Z",
                    "hasAttachments": True,
                    "importance": "high",
                    "isRead": False,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("監査")
        assert len(results) == 1
        assert results[0]["id"] == "msg-001"
        assert results[0]["subject"] == "監査依頼: Q4決算"
        assert results[0]["from_name"] == "田中太郎"
        assert results[0]["from_address"] == "tanaka@example.com"
        assert results[0]["has_attachments"] is True
        assert results[0]["importance"] == "high"
        assert results[0]["source"] == "email"

    @pytest.mark.asyncio
    async def test_search_with_filters(self) -> None:
        """フィルタ付きメール検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        await conn.search(
            "audit",
            user_id="user@example.com",
            folder="inbox",
            from_address="sender@example.com",
            date_from="2025-01-01",
            date_to="2025-12-31",
            has_attachments=True,
            max_results=10,
        )

        call_args = conn._client.get.call_args
        url = call_args.args[0]
        params = call_args.kwargs.get("params", {})
        # フォルダ指定がURLに含まれる
        assert "mailFolders/inbox" in url
        assert "user@example.com" in url
        # フィルタパラメータ
        assert "$filter" in params
        assert "from/emailAddress/address eq 'sender@example.com'" in params["$filter"]
        assert "hasAttachments eq true" in params["$filter"]
        assert "$search" in params
        assert params["$top"] == "10"

    @pytest.mark.asyncio
    async def test_search_without_folder(self) -> None:
        """フォルダ未指定検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        await conn.search("test")

        call_args = conn._client.get.call_args
        url = call_args.args[0]
        assert "mailFolders" not in url

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """検索結果なし"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_not_connected(self) -> None:
        """未接続時は空リスト"""
        with patch("src.connectors.email.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="",
                azure_client_id="",
                azure_client_secret="",
            )
            conn = EmailConnector()
        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_401_retry(self) -> None:
        """401時にトークン再取得してリトライ"""
        conn = _connected_connector()

        error_response = MagicMock()
        error_response.status_code = 401
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=error_response,
        )

        ok_response = MagicMock()
        ok_response.json.return_value = {"value": []}
        ok_response.raise_for_status = MagicMock()

        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "refreshed"}
        token_response.raise_for_status = MagicMock()

        conn._client.get = AsyncMock(side_effect=[error_response, ok_response])
        conn._client.post = AsyncMock(return_value=token_response)

        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_generic_error(self) -> None:
        """一般エラー時は空リスト"""
        conn = _connected_connector()
        conn._client.get = AsyncMock(side_effect=Exception("Network error"))

        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_attachments(self) -> None:
        """メール添付ファイル一覧取得"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "att-001",
                    "name": "report.pdf",
                    "contentType": "application/pdf",
                    "size": 4096,
                    "isInline": False,
                },
                {
                    "id": "att-002",
                    "name": "logo.png",
                    "contentType": "image/png",
                    "size": 1024,
                    "isInline": True,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        attachments = await conn.get_attachments("user@example.com", "msg-001")
        assert len(attachments) == 2
        assert attachments[0]["name"] == "report.pdf"
        assert attachments[0]["is_inline"] is False
        assert attachments[1]["name"] == "logo.png"
        assert attachments[1]["is_inline"] is True

    @pytest.mark.asyncio
    async def test_get_attachments_not_connected(self) -> None:
        """未接続時は空リスト"""
        conn = _create_connector()
        attachments = await conn.get_attachments("user", "msg")
        assert attachments == []

    @pytest.mark.asyncio
    async def test_get_attachments_error(self) -> None:
        """添付取得エラー時は空リスト"""
        conn = _connected_connector()
        conn._client.get = AsyncMock(side_effect=Exception("API error"))

        attachments = await conn.get_attachments("user", "msg")
        assert attachments == []

    @pytest.mark.asyncio
    async def test_get_attachment_content(self) -> None:
        """添付ファイルコンテンツ取得"""
        conn = _connected_connector()
        import base64

        content_bytes = base64.b64encode(b"Hello PDF content").decode()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "contentBytes": content_bytes,
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        content = await conn.get_attachment_content("user@example.com", "msg-001", "att-001")
        assert content == b"Hello PDF content"

    @pytest.mark.asyncio
    async def test_get_attachment_content_empty(self) -> None:
        """空コンテンツ"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"contentBytes": ""}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        content = await conn.get_attachment_content("user", "msg", "att")
        assert content is None

    @pytest.mark.asyncio
    async def test_get_attachment_content_not_connected(self) -> None:
        """未接続時はNone"""
        conn = _create_connector()
        content = await conn.get_attachment_content("user", "msg", "att")
        assert content is None

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
    async def test_health_check_error(self) -> None:
        """ヘルスチェック — APIエラー"""
        conn = _connected_connector()
        conn._client.get = AsyncMock(side_effect=Exception("Network error"))

        assert await conn.health_check() is False

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """切断"""
        conn = _connected_connector()
        await conn.disconnect()
        assert conn._client is None
        assert conn._access_token is None
