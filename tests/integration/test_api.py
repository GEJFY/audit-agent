"""API統合テスト"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.integration
class TestAPIIntegration:
    """API統合テスト"""

    async def test_health_check(self) -> None:
        """ヘルスチェックエンドポイント"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_login(self) -> None:
        """ログインエンドポイント"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "test"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_protected_endpoint_without_auth(self) -> None:
        """認証なしでの保護エンドポイントアクセス"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/projects/")

        assert response.status_code in (401, 403)


@pytest.mark.integration
class TestSecurityHeadersIntegration:
    """セキュリティヘッダー統合テスト"""

    async def test_security_headers_on_health(self) -> None:
        """ヘルスチェックにセキュリティヘッダーが付与される"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    async def test_sql_injection_blocked(self) -> None:
        """SQLインジェクション攻撃がブロックされる"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/projects/",
                params={"q": "1; DROP TABLE projects;--"},
            )

        assert response.status_code == 403

    async def test_xss_attack_blocked(self) -> None:
        """XSS攻撃がブロックされる"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/projects/",
                params={"q": "<script>alert(1)</script>"},
            )

        assert response.status_code == 403


@pytest.mark.integration
class TestDialogueAPIIntegration:
    """対話API統合テスト"""

    async def test_dialogue_endpoint_exists(self) -> None:
        """対話エンドポイントが存在する"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/dialogue/threads")

        # 認証エラーまたは正常応答（エンドポイントの存在確認）
        assert response.status_code in (200, 401, 403)


@pytest.mark.integration
class TestAgentAPIIntegration:
    """Agent API統合テスト"""

    async def test_agents_list(self) -> None:
        """Agent一覧エンドポイント"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/agents/")

        # 認証エラーまたは正常応答
        assert response.status_code in (200, 401, 403)


@pytest.mark.integration
class TestEvidenceAPIIntegration:
    """証跡API統合テスト"""

    async def test_evidence_endpoint_exists(self) -> None:
        """証跡エンドポイントが存在する"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/evidence/")

        assert response.status_code in (200, 401, 403)
