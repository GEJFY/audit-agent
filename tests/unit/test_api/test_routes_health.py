"""ヘルスチェックルートテスト"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.mark.unit
class TestHealthRoutes:
    async def test_health_check(self) -> None:
        """GET /api/v1/health"""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    async def test_liveness(self) -> None:
        """GET /api/v1/health/live"""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    async def test_readiness(self) -> None:
        """GET /api/v1/health/ready"""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/ready")
        # readyは依存サービスの状態による（200 or 503）
        assert resp.status_code in (200, 503)
