"""分析エンドポイント — クロス企業分析・ポートフォリオ"""

from typing import Any

from fastapi import APIRouter, Depends

from src.analytics.cross_company import (
    CompanyRiskProfile,
    CrossCompanyAnalyzer,
)
from src.analytics.portfolio_risk import (
    CompanyRiskSummary,
    PortfolioRiskAggregator,
)
from src.api.middleware.auth import require_permission

router = APIRouter()


@router.post("/benchmark")
async def run_benchmark(
    companies: list[dict[str, Any]],
    user: Any = Depends(require_permission("analytics:benchmark")),
) -> dict[str, Any]:
    """業種ベンチマーク分析を実行

    Body:
        companies: [{company_id, company_name, industry, region, risk_scores, ...}]
    """
    analyzer = CrossCompanyAnalyzer()

    for c in companies:
        analyzer.add_profile(
            CompanyRiskProfile(
                company_id=c["company_id"],
                company_name=c["company_name"],
                industry=c.get("industry", "other"),
                region=c.get("region", "JP"),
                risk_scores=c.get("risk_scores", {}),
                overall_score=c.get("overall_score", 0.0),
                finding_count=c.get("finding_count", 0),
                control_effectiveness=c.get("control_effectiveness", 0.0),
            )
        )

    result = analyzer.analyze()

    return {
        "total_companies": result.total_companies,
        "industries": result.industries,
        "benchmarks": [
            {
                "industry": b.industry,
                "category": b.category,
                "avg_score": b.avg_score,
                "median_score": b.median_score,
                "std_dev": b.std_dev,
                "sample_size": b.sample_size,
            }
            for b in result.benchmarks
        ],
        "comparisons_count": len(result.comparisons),
        "anomaly_correlations_count": len(result.anomaly_correlations),
        "top_risks": result.top_risks[:10],
    }


@router.post("/portfolio")
async def run_portfolio(
    companies: list[dict[str, Any]],
    user: Any = Depends(require_permission("analytics:portfolio")),
) -> dict[str, Any]:
    """ポートフォリオリスク集約を実行

    Body:
        companies: [{company_id, company_name, industry, overall_score, ...}]
    """
    aggregator = PortfolioRiskAggregator()

    for c in companies:
        aggregator.add_company(
            CompanyRiskSummary(
                company_id=c["company_id"],
                company_name=c["company_name"],
                industry=c.get("industry", "other"),
                region=c.get("region", "JP"),
                overall_score=c.get("overall_score", 0.0),
                category_scores=c.get("category_scores", {}),
                trend=c.get("trend", "stable"),
                open_findings=c.get("open_findings", 0),
            )
        )

    result = aggregator.aggregate()

    return {
        "total_companies": result.total_companies,
        "avg_overall_score": result.avg_overall_score,
        "risk_distribution": result.risk_distribution,
        "industry_distribution": result.industry_distribution,
        "alerts_count": len(result.alerts),
        "alerts": [
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "description": a.description,
                "affected_companies": a.affected_companies,
            }
            for a in result.alerts
        ],
        "category_averages": result.category_averages,
    }
