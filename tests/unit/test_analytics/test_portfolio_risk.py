"""ポートフォリオリスク集約 テスト"""

import pytest

from src.analytics.portfolio_risk import (
    CompanyRiskSummary,
    HeatmapCell,
    PortfolioAlert,
    PortfolioRiskAggregator,
    PortfolioSummary,
)


def _sample_companies() -> list[CompanyRiskSummary]:
    """テスト用企業サマリー"""
    return [
        CompanyRiskSummary(
            company_id="C001",
            company_name="A社",
            industry="finance",
            overall_score=85.0,
            category_scores={"financial": 90.0, "it": 80.0},
            trend="worsening",
            open_findings=5,
        ),
        CompanyRiskSummary(
            company_id="C002",
            company_name="B社",
            industry="finance",
            overall_score=65.0,
            category_scores={"financial": 70.0, "it": 60.0},
            trend="stable",
            open_findings=2,
        ),
        CompanyRiskSummary(
            company_id="C003",
            company_name="C社",
            industry="manufacturing",
            overall_score=45.0,
            category_scores={"financial": 40.0, "quality": 50.0},
            trend="improving",
            open_findings=1,
        ),
        CompanyRiskSummary(
            company_id="C004",
            company_name="D社",
            industry="manufacturing",
            overall_score=30.0,
            category_scores={"financial": 25.0, "quality": 35.0},
            trend="stable",
            open_findings=0,
        ),
    ]


@pytest.mark.unit
class TestPortfolioRiskAggregatorBasic:
    """PortfolioRiskAggregator 基本テスト"""

    def test_empty_portfolio(self) -> None:
        """空のポートフォリオ"""
        agg = PortfolioRiskAggregator()
        result = agg.aggregate()

        assert result.total_companies == 0
        assert result.avg_overall_score == 0.0
        assert result.risk_distribution == {}

    def test_add_company(self) -> None:
        """企業追加"""
        agg = PortfolioRiskAggregator()
        agg.add_company(
            CompanyRiskSummary(
                company_id="C001",
                company_name="テスト社",
                industry="finance",
                overall_score=50.0,
            )
        )
        assert len(agg.companies) == 1

    def test_add_companies(self) -> None:
        """一括追加"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        assert len(agg.companies) == 4

    def test_result_type(self) -> None:
        """結果型"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()
        assert isinstance(result, PortfolioSummary)

    def test_clear(self) -> None:
        """クリア"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        agg.clear()
        assert len(agg.companies) == 0


@pytest.mark.unit
class TestRiskClassification:
    """リスクレベル分類テスト"""

    def test_critical_threshold(self) -> None:
        """critical: score >= 80"""
        agg = PortfolioRiskAggregator()
        assert agg._classify_risk_level(85.0) == "critical"
        assert agg._classify_risk_level(80.0) == "critical"

    def test_high_threshold(self) -> None:
        """high: 60 <= score < 80"""
        agg = PortfolioRiskAggregator()
        assert agg._classify_risk_level(65.0) == "high"
        assert agg._classify_risk_level(60.0) == "high"

    def test_medium_threshold(self) -> None:
        """medium: 40 <= score < 60"""
        agg = PortfolioRiskAggregator()
        assert agg._classify_risk_level(50.0) == "medium"
        assert agg._classify_risk_level(40.0) == "medium"

    def test_low_threshold(self) -> None:
        """low: score < 40"""
        agg = PortfolioRiskAggregator()
        assert agg._classify_risk_level(30.0) == "low"
        assert agg._classify_risk_level(0.0) == "low"

    def test_custom_thresholds(self) -> None:
        """カスタム閾値"""
        agg = PortfolioRiskAggregator(
            critical_threshold=90.0,
            high_threshold=70.0,
            medium_threshold=50.0,
        )
        assert agg._classify_risk_level(85.0) == "high"
        assert agg._classify_risk_level(90.0) == "critical"


@pytest.mark.unit
class TestDistributions:
    """分布計算テスト"""

    def test_risk_distribution(self) -> None:
        """リスクレベル分布"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        assert result.risk_distribution["critical"] == 1  # A社 85
        assert result.risk_distribution["high"] == 1  # B社 65
        assert result.risk_distribution["medium"] == 1  # C社 45
        assert result.risk_distribution["low"] == 1  # D社 30

    def test_industry_distribution(self) -> None:
        """業種分布"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        assert result.industry_distribution["finance"] == 2
        assert result.industry_distribution["manufacturing"] == 2

    def test_region_distribution(self) -> None:
        """リージョン分布"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        assert result.region_distribution["JP"] == 4


@pytest.mark.unit
class TestPortfolioScoring:
    """ポートフォリオスコアリング テスト"""

    def test_avg_overall_score(self) -> None:
        """全体平均スコア"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        # (85 + 65 + 45 + 30) / 4 = 56.25
        assert result.avg_overall_score == 56.25

    def test_category_averages(self) -> None:
        """カテゴリ別平均"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        # financial: (90 + 70 + 40 + 25) / 4 = 56.25
        assert result.category_averages["financial"] == 56.25

    def test_top_risk_companies(self) -> None:
        """トップリスク企業（スコア降順）"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        assert len(result.top_risk_companies) <= 10
        assert result.top_risk_companies[0].company_id == "C001"  # 85点


@pytest.mark.unit
class TestHeatmap:
    """ヒートマップ テスト"""

    def test_heatmap_generated(self) -> None:
        """ヒートマップデータが生成される"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        assert len(result.heatmap) > 0

    def test_heatmap_cell_structure(self) -> None:
        """HeatmapCellの構造"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        for cell in result.heatmap:
            assert isinstance(cell, HeatmapCell)
            assert cell.company_id
            assert cell.category
            assert cell.risk_level in ("critical", "high", "medium", "low")

    def test_heatmap_cell_count(self) -> None:
        """ヒートマップセル数 = 企業数 × カテゴリ数"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        # C001: 2, C002: 2, C003: 2, C004: 2 = 8セル
        assert len(result.heatmap) == 8


@pytest.mark.unit
class TestAlerts:
    """アラート生成テスト"""

    def test_critical_threshold_alert(self) -> None:
        """クリティカル企業がある場合のアラート"""
        agg = PortfolioRiskAggregator()
        agg.add_companies(_sample_companies())
        result = agg.aggregate()

        threshold_alerts = [a for a in result.alerts if a.alert_type == "threshold_breach"]
        assert len(threshold_alerts) >= 1
        assert "C001" in threshold_alerts[0].affected_companies

    def test_concentration_risk_alert(self) -> None:
        """集中リスクアラート"""
        # finance業種に高リスク企業が集中
        companies = [
            CompanyRiskSummary(
                company_id=f"F{i:03d}",
                company_name=f"金融{i}社",
                industry="finance",
                overall_score=85.0,
            )
            for i in range(4)
        ] + [
            CompanyRiskSummary(
                company_id="M001",
                company_name="製造1社",
                industry="manufacturing",
                overall_score=30.0,
            )
        ]
        agg = PortfolioRiskAggregator(concentration_alert_pct=0.3)
        agg.add_companies(companies)
        result = agg.aggregate()

        conc_alerts = [a for a in result.alerts if a.alert_type == "concentration_risk"]
        assert len(conc_alerts) >= 1

    def test_trend_worsening_alert(self) -> None:
        """トレンド悪化アラート（3社以上）"""
        companies = [
            CompanyRiskSummary(
                company_id=f"W{i:03d}",
                company_name=f"悪化{i}社",
                industry="finance",
                overall_score=50.0,
                trend="worsening",
            )
            for i in range(4)
        ]
        agg = PortfolioRiskAggregator()
        agg.add_companies(companies)
        result = agg.aggregate()

        trend_alerts = [a for a in result.alerts if a.alert_type == "trend_change"]
        assert len(trend_alerts) >= 1

    def test_no_alerts_low_risk(self) -> None:
        """全企業低リスクならアラートなし"""
        companies = [
            CompanyRiskSummary(
                company_id=f"L{i:03d}",
                company_name=f"低リスク{i}社",
                industry="finance",
                overall_score=20.0,
            )
            for i in range(3)
        ]
        agg = PortfolioRiskAggregator()
        agg.add_companies(companies)
        result = agg.aggregate()

        assert len(result.alerts) == 0

    def test_alert_dataclass(self) -> None:
        """PortfolioAlertデータクラス"""
        alert = PortfolioAlert(
            alert_type="threshold_breach",
            severity="critical",
            description="テスト",
            affected_companies=["C001"],
        )
        assert alert.alert_type == "threshold_breach"
        assert alert.affected_companies == ["C001"]


@pytest.mark.unit
class TestRBACIntegration:
    """RBAC EXECUTIVE ロール テスト"""

    def test_executive_role_exists(self) -> None:
        """EXECUTIVEロールが定義されている"""
        from src.config.constants import UserRole

        assert UserRole.EXECUTIVE == "executive"

    def test_executive_has_analytics_permissions(self) -> None:
        """EXECUTIVEがanalytics権限を持つ"""
        from src.security.rbac import RBACService

        svc = RBACService()
        assert svc.has_permission("executive", "analytics:read")
        assert svc.has_permission("executive", "analytics:benchmark")
        assert svc.has_permission("executive", "analytics:portfolio")

    def test_executive_has_report_read(self) -> None:
        """EXECUTIVEがレポート閲覧権限を持つ"""
        from src.security.rbac import RBACService

        svc = RBACService()
        assert svc.has_permission("executive", "report:read")

    def test_executive_no_admin(self) -> None:
        """EXECUTIVEは管理権限を持たない"""
        from src.security.rbac import RBACService

        svc = RBACService()
        assert not svc.has_permission("executive", "admin:users")
        assert not svc.has_permission("executive", "admin:settings")
