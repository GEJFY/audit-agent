"""相関IDミドルウェアテスト"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.middleware.correlation import CorrelationIdMiddleware


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.unit
class TestCorrelationIdMiddleware:
    async def test_generates_correlation_id(self) -> None:
        """相関IDが自動生成される"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")

        assert resp.status_code == 200
        assert "x-correlation-id" in resp.headers
        assert len(resp.headers["x-correlation-id"]) > 0

    async def test_preserves_existing_correlation_id(self) -> None:
        """既存の相関IDが保持される"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        custom_id = "test-correlation-123"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/test",
                headers={"X-Correlation-ID": custom_id},
            )

        assert resp.status_code == 200
        assert resp.headers["x-correlation-id"] == custom_id
