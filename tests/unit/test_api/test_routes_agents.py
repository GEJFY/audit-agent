"""エージェントエンドポイントテスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
class TestAgentRoutes:
    async def test_list_agents(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """エージェント一覧"""
        resp = await client.get("/api/v1/agents/")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data

    async def test_execute_agent_invalid_body(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """エージェント実行 — バリデーションエラー（必須フィールド不足）"""
        resp = await client.post(
            "/api/v1/agents/execute",
            json={},  # agent_name missing
        )
        assert resp.status_code == 422

    async def test_list_decisions(
        self,
        client: "AsyncClient",
        mock_db_session: AsyncMock,  # noqa: F821
    ) -> None:
        """意思決定一覧"""
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_list = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_list])

        resp = await client.get("/api/v1/agents/decisions")
        assert resp.status_code == 200
