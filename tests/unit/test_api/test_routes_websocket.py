"""WebSocket ConnectionManager テスト"""

from unittest.mock import AsyncMock

import pytest

from src.api.routes.websocket import ConnectionManager


@pytest.mark.unit
class TestConnectionManager:
    def test_init(self) -> None:
        cm = ConnectionManager()
        assert cm.get_active_count() == 0

    async def test_connect(self) -> None:
        cm = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await cm.connect(ws, "tenant-1", "user-1")
        assert cm.get_active_count() >= 1

    async def test_disconnect(self) -> None:
        cm = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await cm.connect(ws, "tenant-1", "user-1")
        cm.disconnect(ws, "tenant-1", "user-1")
        assert cm.get_active_count("tenant-1") == 0

    async def test_send_to_user(self) -> None:
        cm = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        await cm.connect(ws, "tenant-1", "user-1")

        count = await cm.send_to_user("tenant-1", "user-1", {"msg": "test"})
        assert count >= 1
        ws.send_json.assert_called_once()

    async def test_send_to_nonexistent_user(self) -> None:
        cm = ConnectionManager()
        count = await cm.send_to_user("tenant-1", "nobody", {"msg": "test"})
        assert count == 0

    async def test_broadcast_to_tenant(self) -> None:
        cm = ConnectionManager()
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await cm.connect(ws1, "tenant-1", "user-1")
        await cm.connect(ws2, "tenant-1", "user-2")

        count = await cm.broadcast_to_tenant("tenant-1", {"msg": "broadcast"})
        assert count >= 2

    async def test_get_active_count_by_tenant(self) -> None:
        cm = ConnectionManager()
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        await cm.connect(ws1, "tenant-1", "user-1")
        await cm.connect(ws2, "tenant-2", "user-2")

        assert cm.get_active_count("tenant-1") >= 1
        assert cm.get_active_count("tenant-2") >= 1
