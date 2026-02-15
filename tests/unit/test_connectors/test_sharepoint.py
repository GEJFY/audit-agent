"""SharePoint コネクタ ユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.connectors.sharepoint import SharePointConnector


def _create_connector() -> SharePointConnector:
    """テスト用SharePointコネクタ生成"""
    with patch("src.connectors.sharepoint.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
        )
        return SharePointConnector()


def _connected_connector() -> SharePointConnector:
    """接続済みSharePointコネクタ"""
    conn = _create_connector()
    conn._client = AsyncMock()
    conn._access_token = "test_token"
    return conn


@pytest.mark.unit
class TestSharePointConnector:
    """SharePointConnector テスト"""

    def test_connector_name(self) -> None:
        conn = _create_connector()
        assert conn.connector_name == "sharepoint"

    @pytest.mark.asyncio
    async def test_connect_missing_settings(self) -> None:
        """Azure AD設定不完全時は接続失敗"""
        with patch("src.connectors.sharepoint.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="",
                azure_client_id="",
                azure_client_secret="",
            )
            conn = SharePointConnector()
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
        """ドキュメント検索成功"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "hitsContainers": [
                        {
                            "hits": [
                                {
                                    "resource": {
                                        "id": "item-123",
                                        "name": "audit_report.pdf",
                                        "webUrl": "https://sharepoint.com/doc/123",
                                        "size": 2048,
                                        "createdDateTime": "2025-01-01T00:00:00Z",
                                        "lastModifiedDateTime": "2025-06-01T00:00:00Z",
                                        "createdBy": {"user": {"displayName": "TestUser"}},
                                        "file": {"mimeType": "application/pdf"},
                                    },
                                    "summary": "監査報告書の概要...",
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.post = AsyncMock(return_value=mock_response)

        results = await conn.search("audit report")
        assert len(results) == 1
        assert results[0]["id"] == "item-123"
        assert results[0]["name"] == "audit_report.pdf"
        assert results[0]["source"] == "sharepoint"
        assert results[0]["mime_type"] == "application/pdf"
        assert results[0]["created_by"] == "TestUser"

    @pytest.mark.asyncio
    async def test_search_with_file_type(self) -> None:
        """ファイル種類フィルタ付き検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.post = AsyncMock(return_value=mock_response)

        await conn.search("report", file_type="xlsx")

        call_args = conn._client.post.call_args
        body = call_args.kwargs.get("json", {})
        query_string = body["requests"][0]["query"]["queryString"]
        assert "filetype:xlsx" in query_string

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """検索結果なし"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.post = AsyncMock(return_value=mock_response)

        results = await conn.search("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_not_connected(self) -> None:
        """未接続時は空リスト"""
        with patch("src.connectors.sharepoint.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_tenant_id="",
                azure_client_id="",
                azure_client_secret="",
            )
            conn = SharePointConnector()
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

        # connect時のOAuthレスポンス
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "refreshed"}
        token_response.raise_for_status = MagicMock()

        conn._client.post = AsyncMock(side_effect=[error_response, token_response, ok_response])

        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_file_content(self) -> None:
        """ファイルコンテンツダウンロード"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.content = b"PDF file content"
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        content = await conn.get_file_content("drive-item-123")
        assert content == b"PDF file content"

    @pytest.mark.asyncio
    async def test_get_file_content_not_connected(self) -> None:
        """未接続時はNone"""
        conn = _create_connector()
        content = await conn.get_file_content("item-123")
        assert content is None

    @pytest.mark.asyncio
    async def test_get_file_content_error(self) -> None:
        """ダウンロードエラー時はNone"""
        conn = _connected_connector()
        conn._client.get = AsyncMock(side_effect=Exception("Download failed"))

        content = await conn.get_file_content("item-123")
        assert content is None

    @pytest.mark.asyncio
    async def test_list_libraries(self) -> None:
        """ドキュメントライブラリ一覧"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": "lib1", "name": "Documents", "webUrl": "https://sp.com/lib1"},
                {"id": "lib2", "name": "Shared", "webUrl": "https://sp.com/lib2"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        libs = await conn.list_libraries("site-123")
        assert len(libs) == 2
        assert libs[0]["name"] == "Documents"
        assert libs[1]["name"] == "Shared"

    @pytest.mark.asyncio
    async def test_list_libraries_not_connected(self) -> None:
        """未接続時は空リスト"""
        conn = _create_connector()
        libs = await conn.list_libraries("site-123")
        assert libs == []

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
