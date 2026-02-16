"""証跡管理エンドポイントテスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestEvidenceRoutes:
    async def test_list_evidence_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """証跡一覧 — 空"""
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_list = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_list])

        resp = await client.get("/api/v1/evidence/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_get_evidence_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """存在しない証跡取得"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        resp = await client.get("/api/v1/evidence/nonexistent-id")
        assert resp.status_code == 404

    async def test_delete_evidence_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """存在しない証跡削除"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        resp = await client.delete("/api/v1/evidence/nonexistent-id")
        assert resp.status_code == 404
