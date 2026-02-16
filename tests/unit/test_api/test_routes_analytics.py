"""分析エンドポイントテスト"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestAnalyticsRoutes:
    async def test_benchmark_endpoint(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """POST /benchmark — 認証済みでベンチマーク分析を実行"""
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

    async def test_portfolio_endpoint(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """POST /portfolio — 認証済みでポートフォリオ集約を実行"""
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

    async def test_benchmark_unauthenticated(self) -> None:
        """POST /benchmark — 認証なしで401を返す"""
        from fastapi import FastAPI
        from httpx import ASGITransport

        from src.api.routes.analytics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/analytics")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/analytics/benchmark",
                json=[{"company_id": "c1", "company_name": "X"}],
            )
        assert resp.status_code in (401, 403)

    async def test_portfolio_unauthenticated(self) -> None:
        """POST /portfolio — 認証なしで401を返す"""
        from fastapi import FastAPI
        from httpx import ASGITransport

        from src.api.routes.analytics import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/analytics")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/api/v1/analytics/portfolio",
                json=[{"company_id": "c1", "company_name": "X"}],
            )
        assert resp.status_code in (401, 403)
