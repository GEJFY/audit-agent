"""セキュリティミドルウェアテスト"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.middleware.security import (
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)


def _create_test_app() -> FastAPI:
    """テスト用ミニマルアプリ"""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    async def test_security_headers_present(self) -> None:
        """OWASPセキュリティヘッダーが付与される"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")

        assert resp.status_code == 200
        # 主要セキュリティヘッダー
        assert "x-content-type-options" in resp.headers
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in resp.headers

    async def test_xss_protection_header(self) -> None:
        """X-XSS-Protectionヘッダー"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")

        assert "x-xss-protection" in resp.headers


@pytest.mark.unit
class TestRequestValidationMiddleware:
    async def test_normal_request_passes(self) -> None:
        """通常リクエストは通過"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")
        assert resp.status_code == 200

    async def test_sql_injection_blocked(self) -> None:
        """SQLインジェクションパターンがブロックされる"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test?q=1 UNION SELECT * FROM users")
        assert resp.status_code == 403

    async def test_xss_blocked(self) -> None:
        """XSSパターンがブロックされる"""
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test?q=<script>alert(1)</script>")
        assert resp.status_code == 403
