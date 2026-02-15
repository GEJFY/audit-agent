"""レポートエンドポイントテスト"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes.reports import router


def _create_reports_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/reports")
    return app


@pytest.mark.unit
class TestReportsRoutes:
    async def test_executive_summary(self) -> None:
        """POST /executive-summary"""
        app = _create_reports_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/reports/executive-summary",
                params={
                    "company_id": "c1",
                    "company_name": "テスト社",
                    "period_start": "2026-01-01",
                    "period_end": "2026-03-31",
                },
                json={"overall_risk_score": 0.6, "findings": []},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    async def test_executive_summary_markdown(self) -> None:
        """POST /executive-summary/markdown"""
        app = _create_reports_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/reports/executive-summary/markdown",
                params={"company_id": "c1", "company_name": "テスト社"},
                json={"overall_risk_score": 0.6},
            )
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/" in content_type  # text/plain or text/markdown

    async def test_risk_forecast_report(self) -> None:
        """POST /risk-forecast"""
        app = _create_reports_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/reports/risk-forecast",
                params={"company_id": "c1", "company_name": "テスト社"},
                json={
                    "current_score": 0.5,
                    "predicted_scores": [
                        {"month": "2026-04", "score": 0.5},
                        {"month": "2026-05", "score": 0.6},
                        {"month": "2026-06", "score": 0.7},
                    ],
                },
            )
        assert resp.status_code == 200
