"""リスクテンプレートエンドポイント テスト"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.fixture
def tmpl_app():
    """テンプレートルート用テストアプリ"""
    return create_app()


@pytest.fixture
async def tmpl_client(tmpl_app):
    """テンプレートルート用テストクライアント"""
    transport = ASGITransport(app=tmpl_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.unit
class TestListTemplates:
    """GET /risk-templates/ テスト"""

    async def test_list_templates(self, tmpl_client: AsyncClient) -> None:
        """テンプレート一覧取得"""
        resp = await tmpl_client.get("/api/v1/risk-templates/")
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] >= 3  # finance, manufacturing, it_services

    async def test_list_has_finance(self, tmpl_client: AsyncClient) -> None:
        """金融テンプレートが含まれる"""
        resp = await tmpl_client.get("/api/v1/risk-templates/")
        data = resp.json()
        codes = [t["industry_code"] for t in data["templates"]]
        assert "finance" in codes


@pytest.mark.unit
class TestGetIndustries:
    """GET /risk-templates/industries テスト"""

    async def test_get_industries(self, tmpl_client: AsyncClient) -> None:
        """業種コード一覧取得"""
        resp = await tmpl_client.get("/api/v1/risk-templates/industries")
        assert resp.status_code == 200
        data = resp.json()
        assert "industries" in data
        assert "finance" in data["industries"]
        assert "manufacturing" in data["industries"]
        assert "it_services" in data["industries"]


@pytest.mark.unit
class TestGetTemplateDetail:
    """GET /risk-templates/{industry_code} テスト"""

    async def test_get_finance_template(self, tmpl_client: AsyncClient) -> None:
        """金融テンプレート詳細取得"""
        resp = await tmpl_client.get("/api/v1/risk-templates/finance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["industry_code"] == "finance"
        assert data["industry_name"] == "金融業"
        assert data["risk_count"] > 0
        assert data["control_count"] > 0
        assert len(data["risks"]) > 0
        assert len(data["controls"]) > 0

    async def test_get_manufacturing_template(self, tmpl_client: AsyncClient) -> None:
        """製造業テンプレート詳細取得"""
        resp = await tmpl_client.get("/api/v1/risk-templates/manufacturing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["industry_code"] == "manufacturing"

    async def test_get_nonexistent_template(self, tmpl_client: AsyncClient) -> None:
        """存在しないテンプレート → 404"""
        resp = await tmpl_client.get("/api/v1/risk-templates/nonexistent")
        assert resp.status_code == 404


@pytest.mark.unit
class TestGetTemplateRisks:
    """GET /risk-templates/{industry_code}/risks テスト"""

    async def test_get_all_risks(self, tmpl_client: AsyncClient) -> None:
        """全リスク項目取得"""
        resp = await tmpl_client.get("/api/v1/risk-templates/finance/risks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["industry_code"] == "finance"
        assert data["count"] > 0
        assert len(data["risks"]) == data["count"]

    async def test_get_risks_by_category(self, tmpl_client: AsyncClient) -> None:
        """カテゴリでフィルタ"""
        resp = await tmpl_client.get("/api/v1/risk-templates/finance/risks?category=compliance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category_filter"] == "compliance"
        for risk in data["risks"]:
            assert risk["category"] == "compliance"

    async def test_get_risks_nonexistent_category(self, tmpl_client: AsyncClient) -> None:
        """存在しないカテゴリ → 空リスト"""
        resp = await tmpl_client.get("/api/v1/risk-templates/finance/risks?category=nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    async def test_get_risks_nonexistent_template(self, tmpl_client: AsyncClient) -> None:
        """存在しないテンプレート → 404"""
        resp = await tmpl_client.get("/api/v1/risk-templates/nonexistent/risks")
        assert resp.status_code == 404
