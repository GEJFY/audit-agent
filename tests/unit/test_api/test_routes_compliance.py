"""コンプライアンスエンドポイントテスト"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.fixture
def compliance_app():
    """コンプライアンスルート用テストアプリ"""
    return create_app()


@pytest.fixture
async def compliance_client(compliance_app):
    """コンプライアンスルート用テストクライアント"""
    transport = ASGITransport(app=compliance_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.unit
class TestComplianceStatus:
    """GET /compliance/status テスト"""

    async def test_status_default_jp(self, compliance_client: AsyncClient) -> None:
        """デフォルトリージョン（JP）"""
        resp = await compliance_client.get("/api/v1/compliance/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "JP"
        assert data["status"] == "active"
        assert "J-SOX" in data["audit_framework"]

    async def test_status_sg(self, compliance_client: AsyncClient) -> None:
        """シンガポールリージョン"""
        resp = await compliance_client.get("/api/v1/compliance/status?region=SG")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "SG"

    async def test_status_unsupported_region(self, compliance_client: AsyncClient) -> None:
        """未対応リージョン"""
        resp = await compliance_client.get("/api/v1/compliance/status?region=XX")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "supported_regions" in data


@pytest.mark.unit
class TestComplianceCheck:
    """POST /compliance/check テスト"""

    async def test_check_default(self, compliance_client: AsyncClient) -> None:
        """コンプライアンスチェック実行"""
        resp = await compliance_client.post(
            "/api/v1/compliance/check",
            json={"region": "JP", "tenant_id": "t-001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "JP"
        assert "total_checks" in data
        assert "compliance_rate" in data
        assert "results" in data

    async def test_check_with_filter(self, compliance_client: AsyncClient) -> None:
        """特定チェックのみ実行"""
        resp = await compliance_client.post(
            "/api/v1/compliance/check",
            json={
                "region": "JP",
                "tenant_id": "t-001",
                "checks": ["nonexistent-check"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # 存在しないチェックIDでフィルタ → 結果0
        assert data["total_checks"] == 0
