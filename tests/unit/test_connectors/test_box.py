"""Box コネクタ ユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.box import BoxConnector


def _create_connector() -> BoxConnector:
    """テスト用Boxコネクタ生成"""
    with patch("src.connectors.box.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            box_client_id="test_id",
            box_client_secret="test_secret",
            box_enterprise_id="test_ent",
        )
        return BoxConnector()


def _connected_connector() -> BoxConnector:
    """接続済みBoxコネクタ"""
    conn = _create_connector()
    conn._client = AsyncMock()
    conn._access_token = "test_token"
    return conn


@pytest.mark.unit
class TestBoxConnector:
    """BoxConnector テスト"""

    def test_connector_name(self) -> None:
        conn = _create_connector()
        assert conn.connector_name == "box"

    @pytest.mark.asyncio
    async def test_connect_missing_settings(self) -> None:
        """設定不完全時は接続失敗"""
        with patch("src.connectors.box.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                box_client_id="",
                box_client_secret="",
                box_enterprise_id="",
            )
            conn = BoxConnector()
        result = await conn.connect()
        assert result is False

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        """検索成功"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "entries": [
                {
                    "id": "123",
                    "name": "test.pdf",
                    "type": "file",
                    "size": 1024,
                    "created_at": "2024-01-01T00:00:00Z",
                    "modified_at": "2024-01-02T00:00:00Z",
                    "parent": {"name": "Root", "id": "0"},
                    "created_by": {"name": "User"},
                    "shared_link": {"url": "https://box.com/s/abc"},
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        results = await conn.search("audit report")
        assert len(results) == 1
        assert results[0]["id"] == "123"
        assert results[0]["name"] == "test.pdf"
        assert results[0]["source"] == "box"

    @pytest.mark.asyncio
    async def test_search_not_connected(self) -> None:
        """未接続時は空リスト"""
        conn = _create_connector()
        results = await conn.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_filters(self) -> None:
        """フィルタ付き検索"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"entries": []}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        await conn.search(
            "test", folder_id="12345", file_extensions=["pdf", "xlsx"], limit=5
        )

        call_kwargs = conn._client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params["ancestor_folder_ids"] == "12345"
        assert params["file_extensions"] == "pdf,xlsx"
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_file_info(self) -> None:
        """ファイルメタデータ取得"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "name": "test.pdf"}
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        info = await conn.get_file_info("123")
        assert info is not None
        assert info["name"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_file_info_not_connected(self) -> None:
        """未接続時はNone"""
        conn = _create_connector()
        info = await conn.get_file_info("123")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_download_url(self) -> None:
        """ダウンロードURL取得"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"location": "https://dl.box.com/file/123"}
        conn._client.get = AsyncMock(return_value=mock_response)

        url = await conn.get_download_url("123")
        assert url == "https://dl.box.com/file/123"

    @pytest.mark.asyncio
    async def test_list_folder(self) -> None:
        """フォルダ一覧"""
        conn = _connected_connector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "entries": [
                {"id": "1", "name": "file1.pdf", "type": "file"},
                {"id": "2", "name": "subfolder", "type": "folder"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        conn._client.get = AsyncMock(return_value=mock_response)

        items = await conn.list_folder("0")
        assert len(items) == 2

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
