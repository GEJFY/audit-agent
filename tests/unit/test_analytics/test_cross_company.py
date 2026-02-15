"""クロス企業分析 テスト"""

import pytest

from src.analytics.cross_company import (
    AnomalyCorrelation,
    BenchmarkComparison,
    CompanyRiskProfile,
    CrossCompanyAnalyzer,
    CrossCompanyResult,
    IndustryBenchmark,
)


def _finance_profiles() -> list[CompanyRiskProfile]:
    """金融業テスト用プロファイル"""
    return [
        CompanyRiskProfile(
            company_id="F001",
            company_name="金融A社",
            industry="finance",
            risk_scores={
                "financial_process": 75.0,
                "access_control": 60.0,
                "it_general": 50.0,
            },
            overall_score=62.0,
        ),
        CompanyRiskProfile(
            company_id="F002",
            company_name="金融B社",
            industry="finance",
            risk_scores={
                "financial_process": 45.0,
                "access_control": 55.0,
                "it_general": 40.0,
            },
            overall_score=47.0,
        ),
        CompanyRiskProfile(
            company_id="F003",
            company_name="金融C社",
            industry="finance",
            risk_scores={
                "financial_process": 85.0,
                "access_control": 80.0,
                "it_general": 70.0,
            },
            overall_score=78.0,
        ),
    ]


def _mixed_profiles() -> list[CompanyRiskProfile]:
    """複数業種テスト用プロファイル"""
    return [
        *_finance_profiles(),
        CompanyRiskProfile(
            company_id="M001",
            company_name="製造A社",
            industry="manufacturing",
            risk_scores={
                "inventory": 65.0,
                "quality": 40.0,
            },
            overall_score=52.0,
        ),
        CompanyRiskProfile(
            company_id="M002",
            company_name="製造B社",
            industry="manufacturing",
            risk_scores={
                "inventory": 55.0,
                "quality": 70.0,
            },
            overall_score=62.0,
        ),
    ]


@pytest.mark.unit
class TestCrossCompanyAnalyzerBasic:
    """CrossCompanyAnalyzer 基本テスト"""

    def test_empty_analysis(self) -> None:
        """プロファイルなしの分析"""
        analyzer = CrossCompanyAnalyzer()
        result = analyzer.analyze()

        assert result.total_companies == 0
        assert result.industries == []
        assert result.benchmarks == []

    def test_add_profile(self) -> None:
        """プロファイル追加"""
        analyzer = CrossCompanyAnalyzer()
        profile = CompanyRiskProfile(
            company_id="F001",
            company_name="テスト社",
            industry="finance",
        )
        analyzer.add_profile(profile)
        assert len(analyzer.profiles) == 1

    def test_add_profiles(self) -> None:
        """プロファイル一括追加"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        assert len(analyzer.profiles) == 3

    def test_result_type(self) -> None:
        """結果型の確認"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()
        assert isinstance(result, CrossCompanyResult)

    def test_clear(self) -> None:
        """クリア"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        analyzer.clear()
        assert len(analyzer.profiles) == 0


@pytest.mark.unit
class TestBenchmarkCalculation:
    """ベンチマーク算出テスト"""

    def test_benchmarks_created(self) -> None:
        """ベンチマークが作成される"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        assert len(result.benchmarks) > 0

    def test_benchmark_categories(self) -> None:
        """各カテゴリのベンチマークが作成される"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        categories = {b.category for b in result.benchmarks}
        assert "financial_process" in categories
        assert "access_control" in categories
        assert "it_general" in categories

    def test_benchmark_avg(self) -> None:
        """平均スコアの正確性"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        fp_bm = next(
            b for b in result.benchmarks if b.category == "financial_process"
        )
        # (75 + 45 + 85) / 3 ≈ 68.33
        assert fp_bm.avg_score == pytest.approx(68.33, abs=0.1)
        assert fp_bm.sample_size == 3

    def test_benchmark_median(self) -> None:
        """中央値の正確性"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        fp_bm = next(
            b for b in result.benchmarks if b.category == "financial_process"
        )
        # sorted: [45, 75, 85] → median = 75
        assert fp_bm.median_score == 75.0

    def test_benchmark_std_dev(self) -> None:
        """標準偏差が正の値"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        for bm in result.benchmarks:
            assert bm.std_dev >= 0.0

    def test_benchmark_dataclass(self) -> None:
        """IndustryBenchmarkデータクラス"""
        bm = IndustryBenchmark(
            industry="finance",
            category="financial_process",
            avg_score=70.0,
            median_score=68.0,
            std_dev=10.0,
            min_score=50.0,
            max_score=90.0,
            sample_size=5,
        )
        assert bm.industry == "finance"
        assert bm.sample_size == 5

    def test_multiple_industries(self) -> None:
        """複数業種のベンチマーク"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_mixed_profiles())
        result = analyzer.analyze()

        industries = {b.industry for b in result.benchmarks}
        assert "finance" in industries
        assert "manufacturing" in industries


@pytest.mark.unit
class TestBenchmarkComparison:
    """ベンチマーク比較テスト"""

    def test_comparisons_created(self) -> None:
        """比較結果が作成される"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        assert len(result.comparisons) > 0

    def test_comparison_status_above_average(self) -> None:
        """平均以上の企業のステータス"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        # F002は低スコア → above_average (リスクが低い)
        f002_comps = [
            c for c in result.comparisons if c.company_id == "F002"
        ]
        assert len(f002_comps) > 0

    def test_comparison_deviation(self) -> None:
        """偏差値が計算される"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        for comp in result.comparisons:
            assert isinstance(comp.deviation, float)

    def test_comparison_percentile(self) -> None:
        """パーセンタイルが0-100の範囲"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        for comp in result.comparisons:
            assert 0.0 <= comp.percentile <= 100.0

    def test_comparison_dataclass(self) -> None:
        """BenchmarkComparisonデータクラス"""
        comp = BenchmarkComparison(
            company_id="F001",
            company_name="金融A社",
            category="financial_process",
            company_score=75.0,
            benchmark_avg=68.0,
            benchmark_median=70.0,
            percentile=80.0,
            deviation=0.7,
            status="average",
        )
        assert comp.company_id == "F001"
        assert comp.status == "average"


@pytest.mark.unit
class TestAnomalyCorrelation:
    """異常相関検出テスト"""

    def test_co_occurrence_detected(self) -> None:
        """両方高スコア → co_occurrence検出"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles([
            CompanyRiskProfile(
                company_id="A",
                company_name="A社",
                industry="finance",
                risk_scores={"cat1": 80.0},
            ),
            CompanyRiskProfile(
                company_id="B",
                company_name="B社",
                industry="finance",
                risk_scores={"cat1": 90.0},
            ),
        ])
        result = analyzer.analyze()

        co_occs = [
            c for c in result.anomaly_correlations
            if c.pattern == "co_occurrence"
        ]
        assert len(co_occs) >= 1

    def test_inverse_detected(self) -> None:
        """片方高・片方低 → inverse検出"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles([
            CompanyRiskProfile(
                company_id="A",
                company_name="A社",
                industry="finance",
                risk_scores={"cat1": 85.0},
            ),
            CompanyRiskProfile(
                company_id="B",
                company_name="B社",
                industry="finance",
                risk_scores={"cat1": 20.0},
            ),
        ])
        result = analyzer.analyze()

        inverse = [
            c for c in result.anomaly_correlations if c.pattern == "inverse"
        ]
        assert len(inverse) >= 1

    def test_no_anomaly_average_scores(self) -> None:
        """平均的なスコアでは相関なし"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles([
            CompanyRiskProfile(
                company_id="A",
                company_name="A社",
                industry="finance",
                risk_scores={"cat1": 50.0},
            ),
            CompanyRiskProfile(
                company_id="B",
                company_name="B社",
                industry="finance",
                risk_scores={"cat1": 55.0},
            ),
        ])
        result = analyzer.analyze()

        assert len(result.anomaly_correlations) == 0

    def test_anomaly_correlation_dataclass(self) -> None:
        """AnomalyCorrelationデータクラス"""
        ac = AnomalyCorrelation(
            company_a="F001",
            company_b="F003",
            category="financial_process",
            correlation=0.85,
            pattern="co_occurrence",
            description="テスト",
        )
        assert ac.pattern == "co_occurrence"
        assert ac.correlation == 0.85


@pytest.mark.unit
class TestTopRisks:
    """トップリスク集約テスト"""

    def test_top_risks_sorted(self) -> None:
        """トップリスクがスコア降順"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        scores = [r["score"] for r in result.top_risks]
        assert scores == sorted(scores, reverse=True)

    def test_top_risks_max_20(self) -> None:
        """トップリスクは最大20件"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_mixed_profiles())
        result = analyzer.analyze()

        assert len(result.top_risks) <= 20

    def test_top_risks_contain_company_info(self) -> None:
        """トップリスクに企業情報が含まれる"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        for risk in result.top_risks:
            assert "company_id" in risk
            assert "company_name" in risk
            assert "category" in risk
            assert "score" in risk


@pytest.mark.unit
class TestIndustriesList:
    """業種リスト テスト"""

    def test_single_industry(self) -> None:
        """単一業種"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_finance_profiles())
        result = analyzer.analyze()

        assert result.industries == ["finance"]

    def test_multiple_industries(self) -> None:
        """複数業種"""
        analyzer = CrossCompanyAnalyzer()
        analyzer.add_profiles(_mixed_profiles())
        result = analyzer.analyze()

        assert len(result.industries) == 2
        assert "finance" in result.industries
        assert "manufacturing" in result.industries
