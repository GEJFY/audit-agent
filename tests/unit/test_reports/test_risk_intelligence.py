"""リスクインテリジェンスレポート テスト"""

from typing import Any

import pytest

from src.reports.risk_intelligence import (
    ReportMetadata,
    ReportSection,
    RiskIntelligenceReport,
    RiskIntelligenceReportGenerator,
)


def _sample_risk_data() -> dict[str, Any]:
    """テスト用リスクデータ"""
    return {
        "overall_score": 72.0,
        "risk_trend": "worsening",
        "category_scores": {
            "financial_process": 85.0,
            "access_control": 65.0,
            "it_general": 55.0,
        },
        "top_findings": [
            "売上計上プロセスに重要な統制不備",
            "アクセス権限の棚卸が未実施",
        ],
        "forecast": {
            "predicted_score": 78.0,
            "confidence": 0.82,
        },
        "benchmark": {
            "percentile": 75.0,
            "industry_avg": 60.0,
        },
        "process_issues": [
            "承認プロセスの遅延",
            "差戻し件数の増加",
            "手動入力エラーの多発",
        ],
    }


def _sample_forecast_data() -> dict[str, Any]:
    """テスト用予測データ"""
    return {
        "current_score": 65.0,
        "predicted_scores": [
            {"month": "2025-04", "score": 68.0},
            {"month": "2025-05", "score": 72.0},
            {"month": "2025-06", "score": 70.0},
        ],
        "risk_factors": [
            "決算期の業務集中",
            "システム更改予定",
        ],
        "confidence": 0.78,
        "category_forecasts": {
            "financial_process": {"current": 70.0, "predicted": 80.0},
            "access_control": {"current": 55.0, "predicted": 58.0},
        },
    }


@pytest.mark.unit
class TestReportDataclasses:
    """レポートデータクラス テスト"""

    def test_report_section(self) -> None:
        """ReportSectionの作成"""
        section = ReportSection(
            title="サマリー",
            content="テスト内容",
            section_type="summary",
            priority=0,
        )
        assert section.title == "サマリー"
        assert section.data == {}

    def test_report_metadata(self) -> None:
        """ReportMetadataの作成"""
        meta = ReportMetadata(
            report_id="RPT-001",
            title="テストレポート",
            report_type="executive_summary",
        )
        assert meta.report_id == "RPT-001"
        assert meta.region == "JP"

    def test_report_section_count(self) -> None:
        """セクション数のプロパティ"""
        report = RiskIntelligenceReport(
            metadata=ReportMetadata(
                report_id="RPT-001",
                title="テスト",
                report_type="test",
            ),
            sections=[
                ReportSection("A", "a", "summary"),
                ReportSection("B", "b", "risk_overview"),
            ],
        )
        assert report.section_count == 2

    def test_report_get_section(self) -> None:
        """セクションタイプで検索"""
        report = RiskIntelligenceReport(
            metadata=ReportMetadata("RPT", "Test", "test"),
            sections=[
                ReportSection("Summary", "content", "summary"),
                ReportSection("Overview", "content", "risk_overview"),
            ],
        )
        s = report.get_section("summary")
        assert s is not None
        assert s.title == "Summary"

    def test_report_get_section_not_found(self) -> None:
        """存在しないセクションタイプはNone"""
        report = RiskIntelligenceReport(
            metadata=ReportMetadata("RPT", "Test", "test"),
            sections=[],
        )
        assert report.get_section("nonexistent") is None


@pytest.mark.unit
class TestExecutiveSummaryGeneration:
    """エグゼクティブサマリー生成テスト"""

    def test_generate_basic(self) -> None:
        """基本的なレポート生成"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        assert isinstance(report, RiskIntelligenceReport)
        assert report.metadata.report_type == "executive_summary"
        assert report.overall_risk_score == 72.0

    def test_report_has_sections(self) -> None:
        """セクションが生成される"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        # summary, risk_overview, forecast, benchmark, process
        assert report.section_count >= 4

    def test_summary_section_exists(self) -> None:
        """サマリーセクションが含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        summary = report.get_section("summary")
        assert summary is not None
        assert summary.title == "エグゼクティブサマリー"

    def test_risk_overview_section(self) -> None:
        """リスク概観セクション"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        overview = report.get_section("risk_overview")
        assert overview is not None

    def test_forecast_section(self) -> None:
        """予測セクション"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        forecast = report.get_section("forecast")
        assert forecast is not None

    def test_benchmark_section(self) -> None:
        """ベンチマークセクション"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        benchmark = report.get_section("benchmark")
        assert benchmark is not None

    def test_process_section(self) -> None:
        """プロセスセクション"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        process = report.get_section("process")
        assert process is not None

    def test_key_findings_passed_through(self) -> None:
        """主要所見がそのまま含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())

        assert len(report.key_findings) == 2
        assert "売上計上プロセスに重要な統制不備" in report.key_findings

    def test_risk_trend(self) -> None:
        """リスクトレンド"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())
        assert report.risk_trend == "worsening"

    def test_company_info_in_metadata(self) -> None:
        """企業情報がメタデータに反映"""
        gen = RiskIntelligenceReportGenerator(company_id="C001", company_name="テスト社")
        report = gen.generate_executive_summary(_sample_risk_data())

        assert report.metadata.company_id == "C001"
        assert report.metadata.company_name == "テスト社"

    def test_period_in_metadata(self) -> None:
        """期間がメタデータに反映"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(
            _sample_risk_data(),
            period_start="2025-01-01",
            period_end="2025-03-31",
        )
        assert report.metadata.period_start == "2025-01-01"
        assert report.metadata.period_end == "2025-03-31"


@pytest.mark.unit
class TestRecommendations:
    """推奨アクション生成テスト"""

    def test_critical_recommendation(self) -> None:
        """クリティカルレベルの推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {"overall_score": 85.0, "category_scores": {}}
        report = gen.generate_executive_summary(data)

        assert any("クリティカル" in r for r in report.recommendations)

    def test_high_recommendation(self) -> None:
        """高リスクレベルの推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {"overall_score": 65.0, "category_scores": {}}
        report = gen.generate_executive_summary(data)

        assert any("高水準" in r for r in report.recommendations)

    def test_low_risk_recommendation(self) -> None:
        """低リスクの場合のデフォルト推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {"overall_score": 30.0, "category_scores": {}}
        report = gen.generate_executive_summary(data)

        assert any("許容範囲" in r for r in report.recommendations)

    def test_category_critical_recommendation(self) -> None:
        """カテゴリがクリティカルの場合"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "overall_score": 50.0,
            "category_scores": {"access_control": 90.0},
        }
        report = gen.generate_executive_summary(data)

        assert any("access_control" in r for r in report.recommendations)

    def test_forecast_worsening_recommendation(self) -> None:
        """予測悪化の推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "overall_score": 50.0,
            "category_scores": {},
            "forecast": {"predicted_score": 70.0},
        }
        report = gen.generate_executive_summary(data)

        assert any("予測モデル" in r for r in report.recommendations)

    def test_process_issues_recommendation(self) -> None:
        """プロセス課題が多い場合の推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "overall_score": 50.0,
            "category_scores": {},
            "process_issues": ["問題1", "問題2", "問題3"],
        }
        report = gen.generate_executive_summary(data)

        assert any("プロセス分析" in r for r in report.recommendations)


@pytest.mark.unit
class TestMarkdownOutput:
    """マークダウン出力テスト"""

    def test_markdown_contains_title(self) -> None:
        """タイトルが含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())
        md = report.to_markdown()

        assert "# リスクインテリジェンスレポート" in md

    def test_markdown_contains_score(self) -> None:
        """スコアが含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())
        md = report.to_markdown()

        assert "72.0" in md

    def test_markdown_contains_findings(self) -> None:
        """所見が含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())
        md = report.to_markdown()

        assert "主要所見" in md

    def test_markdown_contains_recommendations(self) -> None:
        """推奨アクションが含まれる"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_executive_summary(_sample_risk_data())
        md = report.to_markdown()

        assert "推奨アクション" in md


@pytest.mark.unit
class TestForecastReport:
    """予測リスクレポート テスト"""

    def test_generate_forecast_report(self) -> None:
        """予測レポート生成"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_risk_forecast_report(_sample_forecast_data())

        assert report.metadata.report_type == "risk_forecast"
        assert report.overall_risk_score == 65.0

    def test_forecast_sections(self) -> None:
        """予測レポートのセクション"""
        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_risk_forecast_report(_sample_forecast_data())

        assert report.section_count >= 2

    def test_forecast_trend_worsening(self) -> None:
        """予測スコア上昇 → worsening"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "current_score": 50.0,
            "predicted_scores": [{"month": "2025-06", "score": 70.0}],
            "confidence": 0.8,
        }
        report = gen.generate_risk_forecast_report(data)
        assert report.risk_trend == "worsening"

    def test_forecast_trend_improving(self) -> None:
        """予測スコア低下 → improving"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "current_score": 70.0,
            "predicted_scores": [{"month": "2025-06", "score": 50.0}],
            "confidence": 0.8,
        }
        report = gen.generate_risk_forecast_report(data)
        assert report.risk_trend == "improving"

    def test_forecast_trend_stable(self) -> None:
        """予測スコア安定 → stable"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "current_score": 50.0,
            "predicted_scores": [{"month": "2025-06", "score": 52.0}],
            "confidence": 0.8,
        }
        report = gen.generate_risk_forecast_report(data)
        assert report.risk_trend == "stable"

    def test_low_confidence_recommendation(self) -> None:
        """低信頼度の推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "current_score": 50.0,
            "predicted_scores": [],
            "confidence": 0.3,
        }
        report = gen.generate_risk_forecast_report(data)

        assert any("信頼度が低い" in r for r in report.recommendations)

    def test_category_increase_recommendation(self) -> None:
        """カテゴリ30%上昇の推奨"""
        gen = RiskIntelligenceReportGenerator()
        data = {
            "current_score": 50.0,
            "predicted_scores": [],
            "confidence": 0.8,
            "category_forecasts": {
                "access_control": {"current": 50.0, "predicted": 80.0},
            },
        }
        report = gen.generate_risk_forecast_report(data)

        assert any("30%以上" in r for r in report.recommendations)


@pytest.mark.unit
class TestScoreToLevel:
    """スコア→レベル変換テスト"""

    def test_critical(self) -> None:
        assert RiskIntelligenceReportGenerator._score_to_level(85) == "クリティカル"

    def test_high(self) -> None:
        assert RiskIntelligenceReportGenerator._score_to_level(65) == "高"

    def test_medium(self) -> None:
        assert RiskIntelligenceReportGenerator._score_to_level(45) == "中"

    def test_low(self) -> None:
        assert RiskIntelligenceReportGenerator._score_to_level(20) == "低"
