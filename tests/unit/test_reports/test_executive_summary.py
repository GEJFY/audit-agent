"""ExecutiveSummaryTemplate テスト"""

import pytest

from src.reports.risk_intelligence import (
    ReportMetadata,
    ReportSection,
    RiskIntelligenceReport,
)
from src.reports.templates.executive_summary import (
    ExecutiveSummaryOutput,
    ExecutiveSummaryTemplate,
)


@pytest.fixture
def sample_report() -> RiskIntelligenceReport:
    """テスト用リスクインテリジェンスレポート"""
    return RiskIntelligenceReport(
        metadata=ReportMetadata(
            report_id="RPT-TEST-001",
            title="テストレポート",
            report_type="executive_summary",
            generated_at="2026-01-15T00:00:00",
            period_start="2025-10-01",
            period_end="2025-12-31",
            company_id="COMP-001",
            company_name="テスト株式会社",
            industry="金融",
            region="JP",
        ),
        sections=[
            ReportSection(
                title="エグゼクティブサマリー",
                content="全体リスクスコア: 65.0 (高)",
                section_type="summary",
                priority=0,
                data={"overall_score": 65.0, "risk_trend": "worsening"},
            ),
            ReportSection(
                title="リスクカテゴリ別概観",
                content="",
                section_type="risk_overview",
                priority=1,
                data={"財務リスク": 75.0, "運用リスク": 55.0, "コンプライアンス": 40.0},
            ),
            ReportSection(
                title="予測リスク分析",
                content="",
                section_type="forecast",
                priority=2,
                data={"predicted_score": 72.0, "confidence": 0.85},
            ),
        ],
        overall_risk_score=65.0,
        risk_trend="worsening",
        key_findings=["内部統制の重大な不備を検出", "IT統制のモニタリング不足"],
        recommendations=["統制強化計画を策定してください", "IT統制の見直しを推奨します"],
    )


@pytest.fixture
def empty_report() -> RiskIntelligenceReport:
    """空のレポート"""
    return RiskIntelligenceReport(
        metadata=ReportMetadata(
            report_id="RPT-EMPTY",
            title="空レポート",
            report_type="executive_summary",
        ),
        sections=[],
    )


@pytest.mark.unit
class TestExecutiveSummaryTemplate:
    """エグゼクティブサマリーテンプレートのテスト"""

    def test_render_basic(self, sample_report: RiskIntelligenceReport) -> None:
        """基本レンダリング"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        assert isinstance(result, ExecutiveSummaryOutput)
        assert "テスト株式会社" in result.title
        assert result.overall_score == 65.0
        assert result.overall_level == "high"
        assert result.risk_trend == "worsening"
        assert result.period == "2025-10-01 〜 2025-12-31"
        assert result.generated_at != ""

    def test_render_heatmap(self, sample_report: RiskIntelligenceReport) -> None:
        """リスクヒートマップの生成"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        assert len(result.heatmap) == 3
        # スコア降順
        assert result.heatmap[0].category == "財務リスク"
        assert result.heatmap[0].score == 75.0
        assert result.heatmap[0].level == "high"
        assert result.heatmap[2].category == "コンプライアンス"
        assert result.heatmap[2].level == "medium"

    def test_render_kpis(self, sample_report: RiskIntelligenceReport) -> None:
        """KPI指標の生成"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        labels = [k.label for k in result.kpis]
        assert "全体リスクスコア" in labels
        assert "主要所見数" in labels
        assert "セクション数" in labels
        assert "予測リスクスコア（3ヶ月後）" in labels

    def test_render_extra_kpis(self, sample_report: RiskIntelligenceReport) -> None:
        """追加KPIの生成"""
        extra = [{"label": "ARR", "value": "¥8億", "trend": "improving", "target": "¥10億"}]
        result = ExecutiveSummaryTemplate.render(sample_report, extra_kpis=extra)

        arr_kpi = next(k for k in result.kpis if k.label == "ARR")
        assert arr_kpi.value == "¥8億"
        assert arr_kpi.trend == "improving"
        assert arr_kpi.target == "¥10億"

    def test_render_action_items(self, sample_report: RiskIntelligenceReport) -> None:
        """アクションアイテムの生成"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        assert len(result.action_items) == 2
        # リスクスコア >= 60 なので high
        assert result.action_items[0].priority == "high"

    def test_render_key_findings(self, sample_report: RiskIntelligenceReport) -> None:
        """主要所見の取得"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        assert len(result.key_findings) == 2
        assert "内部統制" in result.key_findings[0]

    def test_render_markdown_contains_sections(self, sample_report: RiskIntelligenceReport) -> None:
        """マークダウン出力の検証"""
        result = ExecutiveSummaryTemplate.render(sample_report)

        assert "# エグゼクティブサマリー" in result.markdown
        assert "## KPI指標" in result.markdown
        assert "## リスクヒートマップ" in result.markdown
        assert "## 主要所見" in result.markdown
        assert "## アクションアイテム" in result.markdown
        assert "テスト株式会社" in result.markdown

    def test_render_empty_report(self, empty_report: RiskIntelligenceReport) -> None:
        """空レポートのレンダリング"""
        result = ExecutiveSummaryTemplate.render(empty_report)

        assert result.overall_score == 0.0
        assert result.overall_level == "low"
        assert len(result.heatmap) == 0
        assert len(result.key_findings) == 0
        assert result.markdown != ""

    def test_score_to_level_critical(self) -> None:
        """クリティカルレベル判定"""
        assert ExecutiveSummaryTemplate._score_to_level(90.0) == "critical"

    def test_score_to_level_high(self) -> None:
        """高レベル判定"""
        assert ExecutiveSummaryTemplate._score_to_level(65.0) == "high"

    def test_score_to_level_medium(self) -> None:
        """中レベル判定"""
        assert ExecutiveSummaryTemplate._score_to_level(45.0) == "medium"

    def test_score_to_level_low(self) -> None:
        """低レベル判定"""
        assert ExecutiveSummaryTemplate._score_to_level(20.0) == "low"
