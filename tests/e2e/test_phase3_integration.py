"""Phase 3 統合E2Eテスト

Phase 3で追加された各機能の統合テスト:
- リージョン設定
- リスクテンプレート → 予測リスク → レポート生成パイプライン
- クロス企業分析 → ポートフォリオ集約パイプライン
- プロセスマイニング → グラフ分析パイプライン
"""

from typing import Any

import pytest

from src.config.regions import get_region_config, list_supported_regions


@pytest.mark.e2e
class TestRegionIntegration:
    """リージョン設定統合テスト"""

    def test_all_regions_valid(self) -> None:
        """全リージョンが有効な設定を持つ"""
        for region_code in list_supported_regions():
            config = get_region_config(region_code)
            assert config.code == region_code
            assert config.timezone
            assert config.accounting_standard
            assert config.currency

    def test_jp_region_j_sox(self) -> None:
        """日本リージョンがJ-SOXフレームワークを持つ"""
        config = get_region_config("JP")
        assert "J-SOX" in config.audit_framework

    def test_data_residency_regions(self) -> None:
        """データレジデンシー要件のあるリージョン"""
        residency_required = [
            code
            for code in list_supported_regions()
            if get_region_config(code).data_residency_required
        ]
        assert "JP" in residency_required
        assert "AU" in residency_required
        assert "KR" in residency_required


@pytest.mark.e2e
class TestRiskPipelineE2E:
    """リスク分析パイプライン統合テスト"""

    def test_risk_to_report_pipeline(self) -> None:
        """リスクデータ → レポート生成の統合フロー"""
        from src.reports.risk_intelligence import (
            RiskIntelligenceReportGenerator,
        )

        # Phase 3 パイプライン: リスクスコア → レポート生成
        risk_data: dict[str, Any] = {
            "overall_score": 72.0,
            "risk_trend": "worsening",
            "category_scores": {
                "financial_process": 85.0,
                "access_control": 65.0,
                "it_general": 45.0,
            },
            "top_findings": [
                "売上計上プロセスに統制不備",
                "アクセスレビュー未実施",
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
                "承認遅延",
                "差戻し増加",
                "手動入力エラー",
            ],
        }

        gen = RiskIntelligenceReportGenerator(
            company_id="C001",
            company_name="テスト金融A社",
        )
        report = gen.generate_executive_summary(
            risk_data,
            period_start="2025-01-01",
            period_end="2025-03-31",
        )

        # レポート構造検証
        assert report.overall_risk_score == 72.0
        assert report.risk_trend == "worsening"
        assert report.section_count >= 5  # summary, overview, forecast, benchmark, process
        assert len(report.key_findings) == 2
        assert len(report.recommendations) >= 1

        # マークダウン出力
        md = report.to_markdown()
        assert "テスト金融A社" not in md  # メタデータはMarkdownタイトルに含まない
        assert "72.0" in md
        assert "推奨アクション" in md

    def test_forecast_report_pipeline(self) -> None:
        """予測データ → 予測レポート生成"""
        from src.reports.risk_intelligence import (
            RiskIntelligenceReportGenerator,
        )

        forecast_data: dict[str, Any] = {
            "current_score": 60.0,
            "predicted_scores": [
                {"month": "2025-04", "score": 65.0},
                {"month": "2025-05", "score": 70.0},
                {"month": "2025-06", "score": 68.0},
            ],
            "confidence": 0.75,
            "risk_factors": ["決算期集中", "システム更改"],
            "category_forecasts": {
                "financial_process": {"current": 65.0, "predicted": 75.0},
                "access_control": {"current": 50.0, "predicted": 52.0},
            },
        }

        gen = RiskIntelligenceReportGenerator()
        report = gen.generate_risk_forecast_report(forecast_data)

        assert report.metadata.report_type == "risk_forecast"
        assert report.risk_trend == "worsening"  # 68 > 60*1.1
        assert report.section_count >= 2


@pytest.mark.e2e
class TestCrossCompanyPipelineE2E:
    """クロス企業分析パイプライン統合テスト"""

    def test_cross_analysis_to_portfolio(self) -> None:
        """クロス分析 → ポートフォリオ集約の統合フロー"""
        from src.analytics.cross_company import (
            CompanyRiskProfile,
            CrossCompanyAnalyzer,
        )
        from src.analytics.portfolio_risk import (
            CompanyRiskSummary,
            PortfolioRiskAggregator,
        )

        # Step 1: クロス分析
        analyzer = CrossCompanyAnalyzer()
        profiles = [
            CompanyRiskProfile(
                company_id=f"C{i:03d}",
                company_name=f"企業{i}",
                industry="finance" if i <= 3 else "manufacturing",
                risk_scores={
                    "financial": 50.0 + i * 10,
                    "operational": 40.0 + i * 5,
                },
                overall_score=45.0 + i * 8,
            )
            for i in range(1, 7)
        ]
        analyzer.add_profiles(profiles)
        cross_result = analyzer.analyze()

        assert cross_result.total_companies == 6
        assert len(cross_result.industries) == 2
        assert len(cross_result.benchmarks) >= 2

        # Step 2: ポートフォリオ集約
        aggregator = PortfolioRiskAggregator()
        for p in profiles:
            aggregator.add_company(
                CompanyRiskSummary(
                    company_id=p.company_id,
                    company_name=p.company_name,
                    industry=p.industry,
                    overall_score=p.overall_score,
                    category_scores=p.risk_scores,
                )
            )

        portfolio = aggregator.aggregate()

        assert portfolio.total_companies == 6
        assert portfolio.avg_overall_score > 0
        assert len(portfolio.heatmap) > 0
        assert "finance" in portfolio.industry_distribution
        assert "manufacturing" in portfolio.industry_distribution


@pytest.mark.e2e
class TestProcessAnalysisPipelineE2E:
    """プロセス分析パイプライン統合テスト"""

    def test_process_mining_full_flow(self) -> None:
        """プロセスマイニング完全フロー"""
        from src.ml.process_mining import ProcessMiner

        events = [
            {"case_id": f"C{i:03d}", "activity": "入力", "timestamp": f"2025-01-{i:02d}T09:00:00"}
            for i in range(1, 6)
        ]
        events += [
            {"case_id": f"C{i:03d}", "activity": "承認", "timestamp": f"2025-01-{i:02d}T10:00:00"}
            for i in range(1, 6)
        ]
        events += [
            {"case_id": f"C{i:03d}", "activity": "転記", "timestamp": f"2025-01-{i:02d}T11:00:00"}
            for i in range(1, 6)
        ]
        events += [
            {"case_id": f"C{i:03d}", "activity": "完了", "timestamp": f"2025-01-{i:02d}T12:00:00"}
            for i in range(1, 6)
        ]
        # 逸脱ケース: 承認スキップ
        events += [
            {"case_id": "C006", "activity": "入力", "timestamp": "2025-01-06T09:00:00"},
            {"case_id": "C006", "activity": "転記", "timestamp": "2025-01-06T10:00:00"},
            {"case_id": "C006", "activity": "完了", "timestamp": "2025-01-06T11:00:00"},
        ]

        miner = ProcessMiner()
        standard_path = ["入力", "承認", "転記", "完了"]
        result = miner.analyze(events, standard_path=standard_path)

        assert result.total_cases == 6
        assert result.conformance_rate < 1.0  # 1件逸脱あり
        assert len(result.deviations) >= 1
        assert len(result.variants) >= 1

    def test_graph_analysis_full_flow(self) -> None:
        """グラフ分析完全フロー"""
        from src.ml.graph_analysis import RiskGraphAnalyzer

        risks = [
            {"id": "R001", "name": "売上リスク", "score": 80, "category": "financial"},
            {"id": "R002", "name": "在庫リスク", "score": 60, "category": "operational"},
            {"id": "R003", "name": "ITリスク", "score": 70, "category": "it"},
        ]
        controls = [
            {"id": "C001", "name": "売上照合", "risk_id": "R001"},
            {"id": "C002", "name": "棚卸", "risk_id": "R002"},
            {"id": "C003", "name": "アクセスレビュー", "risk_id": "R003"},
            {"id": "C004", "name": "承認フロー", "risk_id": "R001"},
        ]

        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(risks, controls)
        result = analyzer.analyze()

        assert result.total_nodes == 7  # 3 risks + 4 controls
        assert result.total_edges == 4
        assert len(result.centrality_ranking) == 7
        assert 0.0 <= result.density <= 1.0


@pytest.mark.e2e
class TestSettingsIntegration:
    """設定統合テスト"""

    def test_settings_with_region(self) -> None:
        """Settingsにリージョン設定を組み合わせ"""
        from src.config.regions import get_region_config
        from src.config.settings import Settings

        settings = Settings(
            app_env="test",
            aws_region="ap-northeast-1",
        )
        region = get_region_config("JP")

        assert settings.app_env == "test"
        assert region.timezone == "Asia/Tokyo"
        assert settings.aws_region == "ap-northeast-1"

    def test_multi_region_deployment(self) -> None:
        """マルチリージョンデプロイ設定"""
        from src.config.regions import get_region_config

        regions = ["JP", "SG", "AU"]
        configs = [get_region_config(r) for r in regions]

        timezones = {c.timezone for c in configs}
        assert len(timezones) == 3  # 全て異なるTZ

        languages = {c.language for c in configs}
        assert "ja" in languages
        assert "en" in languages
