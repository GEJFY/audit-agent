"""レポートエンドポイント — リスクインテリジェンスレポート生成"""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src.reports.risk_intelligence import RiskIntelligenceReportGenerator

router = APIRouter()


@router.post("/executive-summary")
async def generate_executive_summary(
    risk_data: dict[str, Any],
    company_id: str = "",
    company_name: str = "",
    period_start: str = "",
    period_end: str = "",
) -> dict[str, Any]:
    """エグゼクティブサマリーレポートを生成"""
    generator = RiskIntelligenceReportGenerator(
        company_id=company_id,
        company_name=company_name,
    )

    report = generator.generate_executive_summary(
        risk_data=risk_data,
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "report_id": report.metadata.report_id,
        "title": report.metadata.title,
        "overall_risk_score": report.overall_risk_score,
        "risk_trend": report.risk_trend,
        "section_count": report.section_count,
        "key_findings": report.key_findings,
        "recommendations": report.recommendations,
    }


@router.post("/executive-summary/markdown")
async def generate_executive_summary_markdown(
    risk_data: dict[str, Any],
    company_id: str = "",
    company_name: str = "",
    period_start: str = "",
    period_end: str = "",
) -> PlainTextResponse:
    """エグゼクティブサマリーをマークダウン形式で取得"""
    generator = RiskIntelligenceReportGenerator(
        company_id=company_id,
        company_name=company_name,
    )

    report = generator.generate_executive_summary(
        risk_data=risk_data,
        period_start=period_start,
        period_end=period_end,
    )

    return PlainTextResponse(
        content=report.to_markdown(),
        media_type="text/markdown",
    )


@router.post("/risk-forecast")
async def generate_risk_forecast_report(
    forecast_data: dict[str, Any],
    company_id: str = "",
    company_name: str = "",
    period_start: str = "",
    period_end: str = "",
) -> dict[str, Any]:
    """予測リスクレポートを生成"""
    generator = RiskIntelligenceReportGenerator(
        company_id=company_id,
        company_name=company_name,
    )

    report = generator.generate_risk_forecast_report(
        forecast_data=forecast_data,
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "report_id": report.metadata.report_id,
        "title": report.metadata.title,
        "overall_risk_score": report.overall_risk_score,
        "risk_trend": report.risk_trend,
        "section_count": report.section_count,
        "recommendations": report.recommendations,
    }
