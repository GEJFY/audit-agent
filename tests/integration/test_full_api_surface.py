"""全APIサーフェス統合テスト

全登録ルーターのエンドポイントが正しく動作することを確認。
"""

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.api.middleware.auth import get_current_user
from src.api.routes import analytics, reports
from src.security.auth import TokenPayload


async def _mock_current_user() -> TokenPayload:
    """テスト用: 認証をバイパスするダミーユーザー"""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub="test-user",
        role="admin",
        tenant_id="test-tenant",
        exp=now,
        iat=now,
        jti="test-jti",
        token_type="access",
    )


def _create_full_app() -> FastAPI:
    """全ルーター登録済みのテスト用アプリを構築

    mainに未登録のルーターも含めてテスト。
    認証依存性をオーバーライドしてテスト可能にする。
    """
    test_app = FastAPI()
    test_app.include_router(reports.router, prefix="/api/v1/reports")
    test_app.include_router(analytics.router, prefix="/api/v1/analytics")
    test_app.dependency_overrides[get_current_user] = _mock_current_user
    return test_app


@pytest.fixture
async def client():
    """メインアプリ用クライアント"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def full_client():
    """全ルーター用クライアント"""
    test_app = _create_full_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.integration
class TestComplianceIntegration:
    """コンプライアンスAPI統合テスト"""

    async def test_compliance_status(self, client: AsyncClient) -> None:
        """コンプライアンス状況取得"""
        resp = await client.get("/api/v1/compliance/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["region"] == "JP"
        assert data["status"] == "active"

    async def test_compliance_check(self, client: AsyncClient) -> None:
        """コンプライアンスチェック実行"""
        resp = await client.post(
            "/api/v1/compliance/check",
            json={"region": "JP", "tenant_id": "t-int-001"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_checks"] > 0
        assert "compliance_rate" in data

    async def test_compliance_multiregion(self, client: AsyncClient) -> None:
        """複数リージョンのコンプライアンスチェック"""
        for region in ["JP", "SG"]:
            resp = await client.get(f"/api/v1/compliance/status?region={region}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["region"] == region


@pytest.mark.integration
class TestReportsIntegration:
    """レポートAPI統合テスト"""

    async def test_executive_summary_generation(self, full_client: AsyncClient) -> None:
        """エグゼクティブサマリー生成フロー"""
        resp = await full_client.post(
            "/api/v1/reports/executive-summary",
            params={
                "company_id": "int-comp-001",
                "company_name": "統合テスト株式会社",
                "period_start": "2025-04-01",
                "period_end": "2025-06-30",
            },
            json={
                "financial_risk": {"score": 3.2, "trend": "stable"},
                "operational_risk": {"score": 2.8, "trend": "improving"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] != ""
        assert data["section_count"] >= 0

    async def test_executive_summary_markdown(self, full_client: AsyncClient) -> None:
        """マークダウン形式レポート生成"""
        resp = await full_client.post(
            "/api/v1/reports/executive-summary/markdown",
            json={"overall_risk_score": 0.6},
        )
        assert resp.status_code == 200
        assert "#" in resp.text

    async def test_risk_forecast_report(self, full_client: AsyncClient) -> None:
        """予測リスクレポート生成"""
        resp = await full_client.post(
            "/api/v1/reports/risk-forecast",
            json={"predictions": [], "time_horizon": "90d"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report_id" in data


@pytest.mark.integration
class TestAnalyticsIntegration:
    """分析API統合テスト"""

    async def test_benchmark_analysis(self, full_client: AsyncClient) -> None:
        """ベンチマーク分析フロー"""
        companies = [
            {
                "company_id": f"int-c{i}",
                "company_name": f"統合テスト社{i}",
                "industry": "manufacturing",
                "risk_scores": {"financial": 0.3 + i * 0.1},
                "overall_score": 0.3 + i * 0.1,
                "finding_count": i * 2,
                "control_effectiveness": 0.8 - i * 0.05,
            }
            for i in range(3)
        ]
        resp = await full_client.post(
            "/api/v1/analytics/benchmark",
            json=companies,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_companies"] == 3

    async def test_portfolio_aggregation(self, full_client: AsyncClient) -> None:
        """ポートフォリオリスク集約フロー"""
        companies = [
            {
                "company_id": "int-p1",
                "company_name": "統合テスト社A",
                "industry": "finance",
                "overall_score": 0.6,
                "category_scores": {"financial": 0.7, "operational": 0.5},
            },
            {
                "company_id": "int-p2",
                "company_name": "統合テスト社B",
                "industry": "it_services",
                "overall_score": 0.4,
            },
        ]
        resp = await full_client.post(
            "/api/v1/analytics/portfolio",
            json=companies,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_companies"] == 2
        assert "avg_overall_score" in data


@pytest.mark.integration
class TestCrossEndpointFlow:
    """エンドポイント横断フローテスト"""

    async def test_health_to_compliance(self, client: AsyncClient) -> None:
        """ヘルスチェック → コンプライアンスチェック"""
        health_resp = await client.get("/api/v1/health/live")
        assert health_resp.status_code == 200

        comp_resp = await client.post(
            "/api/v1/compliance/check",
            json={"region": "JP"},
        )
        assert comp_resp.status_code == 200

    async def test_benchmark_to_report(self, full_client: AsyncClient) -> None:
        """ベンチマーク分析 → レポート生成のフロー"""
        bench_resp = await full_client.post(
            "/api/v1/analytics/benchmark",
            json=[
                {
                    "company_id": "flow-c1",
                    "company_name": "フロー社A",
                    "industry": "finance",
                    "risk_scores": {"financial": 0.5},
                    "overall_score": 0.5,
                },
            ],
        )
        assert bench_resp.status_code == 200
        bench_data = bench_resp.json()

        report_resp = await full_client.post(
            "/api/v1/reports/executive-summary",
            params={"company_id": "flow-c1", "company_name": "フロー社A"},
            json={
                "benchmark_result": bench_data,
                "overall_score": 0.5,
            },
        )
        assert report_resp.status_code == 200
        assert report_resp.json()["report_id"] != ""

    async def test_all_public_endpoints_reachable(self, client: AsyncClient) -> None:
        """全公開エンドポイントがアクセス可能"""
        public_endpoints = [
            ("GET", "/api/v1/health/live"),
            ("GET", "/api/v1/compliance/status"),
        ]
        for method, path in public_endpoints:
            if method == "GET":
                resp = await client.get(path)
            else:
                resp = await client.post(path, json={})
            assert resp.status_code != 404, f"{method} {path} returned 404"
