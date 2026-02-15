"""RiskForecastTemplate テスト"""

import pytest

from src.reports.risk_intelligence import (
    ReportMetadata,
    ReportSection,
    RiskIntelligenceReport,
)
from src.reports.templates.risk_forecast import (
    RiskForecastOutput,
    RiskForecastTemplate,
)


@pytest.fixture
def forecast_data() -> dict:
    """テスト用予測データ"""
    return {
        "current_score": 55.0,
        "predicted_scores": [
            {"month": "2026-02", "score": 58.0, "lower": 52.0, "upper": 64.0},
            {"month": "2026-03", "score": 62.0, "lower": 55.0, "upper": 69.0},
            {"month": "2026-04", "score": 65.0, "lower": 57.0, "upper": 73.0},
        ],
        "confidence": 0.82,
        "category_forecasts": {
            "財務リスク": {"current": 50.0, "predicted": 65.0},
            "運用リスク": {"current": 60.0, "predicted": 58.0},
            "コンプライアンス": {"current": 40.0, "predicted": 41.0},
        },
        "risk_factors": ["規制変更の影響", "人員不足による統制低下"],
    }


@pytest.fixture
def sample_forecast_report() -> RiskIntelligenceReport:
    """テスト用予測レポート"""
    return RiskIntelligenceReport(
        metadata=ReportMetadata(
            report_id="RPT-FC-TEST",
            title="予測リスクレポート",
            report_type="risk_forecast",
            period_start="2026-01-01",
            period_end="2026-04-30",
            company_name="テスト企業",
        ),
        sections=[
            ReportSection(
                title="予測サマリー",
                content="",
                section_type="summary",
                priority=0,
                data={"current": 55.0, "predicted": [{"month": "2026-04", "score": 65.0}]},
            ),
            ReportSection(
                title="予測リスク分析",
                content="",
                section_type="forecast",
                priority=1,
                data={
                    "predicted_score": 65.0,
                    "confidence": 0.8,
                    "predicted": [{"month": "2026-04", "score": 65.0}],
                    "category_forecasts": {"財務": {"current": 50.0, "predicted": 60.0}},
                },
            ),
        ],
        overall_risk_score=55.0,
        risk_trend="worsening",
        key_findings=["予測信頼度: 80%"],
    )


@pytest.mark.unit
class TestRiskForecastTemplate:
    """予測リスクレポートテンプレートのテスト"""

    def test_render_basic(self, forecast_data: dict) -> None:
        """基本レンダリング"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            predicted_scores=forecast_data["predicted_scores"],
            confidence=forecast_data["confidence"],
            company_name="テスト企業",
        )

        assert isinstance(result, RiskForecastOutput)
        assert result.current_score == 55.0
        assert result.confidence == 0.82
        assert "テスト企業" in result.title

    def test_forecast_points(self, forecast_data: dict) -> None:
        """予測ポイントの構築"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            predicted_scores=forecast_data["predicted_scores"],
            confidence=forecast_data["confidence"],
        )

        assert len(result.forecast_points) == 3
        assert result.forecast_points[0].month == "2026-02"
        assert result.forecast_points[0].predicted_score == 58.0
        assert result.forecast_points[0].lower_bound == 52.0
        assert result.forecast_points[0].upper_bound == 64.0

    def test_category_forecasts(self, forecast_data: dict) -> None:
        """カテゴリ別予測"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            category_forecasts=forecast_data["category_forecasts"],
            confidence=forecast_data["confidence"],
        )

        assert len(result.category_forecasts) == 3
        # 変化量の絶対値が大きい順
        assert result.category_forecasts[0].category == "財務リスク"
        assert result.category_forecasts[0].direction == "up"
        assert result.category_forecasts[0].change == 15.0

    def test_category_forecast_direction_down(self, forecast_data: dict) -> None:
        """カテゴリ予測の下降方向"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            category_forecasts=forecast_data["category_forecasts"],
            confidence=forecast_data["confidence"],
        )

        ops_forecast = next(f for f in result.category_forecasts if f.category == "運用リスク")
        assert ops_forecast.direction == "down"

    def test_category_forecast_stable(self, forecast_data: dict) -> None:
        """カテゴリ予測の安定方向"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            category_forecasts=forecast_data["category_forecasts"],
            confidence=forecast_data["confidence"],
        )

        comp_forecast = next(f for f in result.category_forecasts if f.category == "コンプライアンス")
        assert comp_forecast.direction == "stable"

    def test_scenario_analysis(self, forecast_data: dict) -> None:
        """シナリオ分析の生成"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            predicted_scores=forecast_data["predicted_scores"],
            confidence=forecast_data["confidence"],
        )

        assert len(result.scenarios) == 3
        scenarios_map = {s.scenario: s for s in result.scenarios}
        assert "best_case" in scenarios_map
        assert "base_case" in scenarios_map
        assert "worst_case" in scenarios_map
        assert scenarios_map["base_case"].predicted_score == 65.0
        assert scenarios_map["best_case"].predicted_score < scenarios_map["base_case"].predicted_score
        assert scenarios_map["worst_case"].predicted_score > scenarios_map["base_case"].predicted_score

    def test_scenario_empty_when_no_predictions(self) -> None:
        """予測なしの場合シナリオ空"""
        result = RiskForecastTemplate.render(current_score=50.0)
        assert len(result.scenarios) == 0

    def test_recommendations_low_confidence(self) -> None:
        """低信頼度時の推奨"""
        result = RiskForecastTemplate.render(
            current_score=50.0,
            confidence=0.3,
        )
        assert any("信頼度" in r for r in result.recommendations)

    def test_recommendations_rising_risk(self, forecast_data: dict) -> None:
        """リスク上昇時の推奨"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            predicted_scores=forecast_data["predicted_scores"],
            confidence=forecast_data["confidence"],
            category_forecasts=forecast_data["category_forecasts"],
        )
        assert any("上昇" in r or "顕著" in r for r in result.recommendations)

    def test_recommendations_stable(self) -> None:
        """安定時の推奨"""
        result = RiskForecastTemplate.render(
            current_score=50.0,
            predicted_scores=[{"month": "2026-02", "score": 50.0}],
            confidence=0.9,
        )
        assert any("安定" in r for r in result.recommendations)

    def test_markdown_output(self, forecast_data: dict) -> None:
        """マークダウン出力"""
        result = RiskForecastTemplate.render(
            current_score=forecast_data["current_score"],
            predicted_scores=forecast_data["predicted_scores"],
            confidence=forecast_data["confidence"],
            category_forecasts=forecast_data["category_forecasts"],
            risk_factors=forecast_data["risk_factors"],
            company_name="テスト企業",
        )

        assert "# 予測リスクレポート" in result.markdown
        assert "## 3ヶ月リスク予測" in result.markdown
        assert "## カテゴリ別予測" in result.markdown
        assert "## シナリオ分析" in result.markdown
        assert "## リスク要因" in result.markdown

    def test_render_from_report(self, sample_forecast_report: RiskIntelligenceReport) -> None:
        """RiskIntelligenceReportからの生成"""
        result = RiskForecastTemplate.render_from_report(sample_forecast_report)

        assert isinstance(result, RiskForecastOutput)
        assert result.current_score == 55.0
        assert "テスト企業" in result.title

    def test_default_bounds_when_not_specified(self) -> None:
        """信頼区間のデフォルト値"""
        result = RiskForecastTemplate.render(
            current_score=50.0,
            predicted_scores=[{"month": "2026-02", "score": 60.0}],
            confidence=0.8,
        )

        assert len(result.forecast_points) == 1
        assert result.forecast_points[0].lower_bound == 50.0  # score - 10
        assert result.forecast_points[0].upper_bound == 70.0  # score + 10
