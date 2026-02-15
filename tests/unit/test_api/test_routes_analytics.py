"""分析エンドポイントテスト"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes.analytics import router


def _create_analytics_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/analytics")
    return app


@pytest.mark.unit
class TestAnalyticsRoutes:
    async def test_benchmark_endpoint(self) -> None:
        """POST /benchmark"""
        app = _create_analytics_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analytics/benchmark",
                json=[
                    {
                        "company_id": "c1",
                        "company_name": "テスト社A",
                        "industry": "manufacturing",
                        "risk_scores": {"financial": 0.5},
                        "overall_score": 0.5,
                    },
                    {
                        "company_id": "c2",
                        "company_name": "テスト社B",
                        "industry": "manufacturing",
                        "risk_scores": {"financial": 0.7},
                        "overall_score": 0.7,
                    },
                ],
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_companies" in data

    async def test_portfolio_endpoint(self) -> None:
        """POST /portfolio"""
        app = _create_analytics_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analytics/portfolio",
                json=[
                    {
                        "company_id": "c1",
                        "company_name": "テスト社A",
                        "industry": "manufacturing",
                        "overall_score": 0.5,
                    },
                ],
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_companies" in data
