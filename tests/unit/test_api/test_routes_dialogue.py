"""対話エンドポイントテスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
class TestDialogueRoutes:
    async def test_list_messages_empty(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """メッセージ一覧 — 空"""
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_list = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_list])

        resp = await client.get("/api/v1/dialogue/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_send_message_invalid_body(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """メッセージ送信 — バリデーションエラー"""
        resp = await client.post(
            "/api/v1/dialogue/send",
            json={"content": "テスト"},  # to_tenant_id, message_type missing
        )
        assert resp.status_code == 422

    async def test_get_thread(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """スレッド取得"""
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_list = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_list])

        resp = await client.get("/api/v1/dialogue/threads/thread-001")
        assert resp.status_code == 200
