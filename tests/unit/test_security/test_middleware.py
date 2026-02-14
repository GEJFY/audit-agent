"""Security Middleware テスト"""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.middleware.security import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    IPThrottleMiddleware,
)


def _create_test_app(*middlewares: type) -> FastAPI:
    """テスト用ミニアプリ生成"""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint() -> dict:
        return {"status": "ok"}

    for mw in middlewares:
        app.add_middleware(mw)

    return app


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """セキュリティヘッダーミドルウェアのテスト"""

    def test_headers_added(self) -> None:
        """OWASPヘッダーが付与されること"""
        app = _create_test_app(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=" in response.headers["Strict-Transport-Security"]
        assert "default-src" in response.headers["Content-Security-Policy"]
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in response.headers["Permissions-Policy"]


@pytest.mark.unit
class TestRequestValidationMiddleware:
    """リクエストバリデーションミドルウェアのテスト"""

    def test_normal_request(self) -> None:
        """正常リクエストは通過"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

    def test_sql_injection_path(self) -> None:
        """SQLインジェクションパスをブロック"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test'; DROP TABLE users;--")
        assert response.status_code == 403

    def test_sql_injection_query(self) -> None:
        """SQLインジェクションクエリパラメータをブロック"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test", params={"q": "1 UNION SELECT * FROM users"})
        assert response.status_code == 403

    def test_xss_path(self) -> None:
        """XSSパスをブロック"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test/<script>alert(1)</script>")
        assert response.status_code == 403

    def test_xss_query(self) -> None:
        """XSSクエリパラメータをブロック"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test", params={"q": "javascript:alert(1)"})
        assert response.status_code == 403

    def test_path_traversal(self) -> None:
        """パストラバーサルをブロック"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/test/../../etc/passwd")
        assert response.status_code == 403

    def test_safe_query_params(self) -> None:
        """安全なクエリパラメータは通過"""
        app = _create_test_app(RequestValidationMiddleware)
        client = TestClient(app)

        response = client.get("/test", params={"q": "normal search query"})
        assert response.status_code == 200


@pytest.mark.unit
class TestIPThrottleMiddleware:
    """IPスロットリングミドルウェアのテスト"""

    def test_normal_traffic(self) -> None:
        """通常トラフィックは通過"""
        app = _create_test_app()
        app.add_middleware(IPThrottleMiddleware, max_requests_per_minute=10)
        client = TestClient(app)

        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_rate_limit_exceeded(self) -> None:
        """レート制限超過時は429"""
        app = _create_test_app()
        app.add_middleware(IPThrottleMiddleware, max_requests_per_minute=3)
        client = TestClient(app)

        responses = []
        for _ in range(5):
            responses.append(client.get("/test"))

        # 最初の数リクエストは成功、超過後は429
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
        assert status_codes[0] == 200
