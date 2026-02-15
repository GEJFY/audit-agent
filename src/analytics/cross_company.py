"""クロス企業分析 — 企業間異常相関・業種ベンチマーク

複数企業のリスクスコアを横断的に比較し、
業種ベンチマークとの乖離分析・企業間の異常相関検出を実施。
"""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class CompanyRiskProfile:
    """企業リスクプロファイル"""

    company_id: str
    company_name: str
    industry: str
    region: str = "JP"
    risk_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    finding_count: int = 0
    control_effectiveness: float = 0.0


@dataclass
class BenchmarkComparison:
    """ベンチマーク比較結果"""

    company_id: str
    company_name: str
    category: str
    company_score: float
    benchmark_avg: float
    benchmark_median: float
    percentile: float  # 0-100
    deviation: float  # 標準偏差からの乖離
    status: str  # above_average, average, below_average, critical


@dataclass
class AnomalyCorrelation:
    """企業間の異常相関"""

    company_a: str
    company_b: str
    category: str
    correlation: float  # -1 to 1
    pattern: str  # co_occurrence, inverse, independent
    description: str


@dataclass
class IndustryBenchmark:
    """業種ベンチマーク"""

    industry: str
    category: str
    avg_score: float
    median_score: float
    std_dev: float
    min_score: float
    max_score: float
    sample_size: int


@dataclass
class CrossCompanyResult:
    """クロス企業分析結果"""

    total_companies: int
    industries: list[str]
    benchmarks: list[IndustryBenchmark]
    comparisons: list[BenchmarkComparison]
    anomaly_correlations: list[AnomalyCorrelation]
    top_risks: list[dict[str, Any]]


class CrossCompanyAnalyzer:
    """クロス企業分析エンジン

    複数企業のリスクデータを横断分析し、
    業種ベンチマーク比較・異常相関検出を実施。
    """

    def __init__(self) -> None:
        self._profiles: list[CompanyRiskProfile] = []

    def add_profile(self, profile: CompanyRiskProfile) -> None:
        """企業プロファイル追加"""
        self._profiles.append(profile)

    def add_profiles(self, profiles: list[CompanyRiskProfile]) -> None:
        """企業プロファイル一括追加"""
        self._profiles.extend(profiles)

    @property
    def profiles(self) -> list[CompanyRiskProfile]:
        """登録済み企業プロファイル"""
        return self._profiles

    def analyze(self) -> CrossCompanyResult:
        """クロス企業分析を実行"""
        if not self._profiles:
            return CrossCompanyResult(
                total_companies=0,
                industries=[],
                benchmarks=[],
                comparisons=[],
                anomaly_correlations=[],
                top_risks=[],
            )

        industries = list({p.industry for p in self._profiles})

        # 業種ベンチマーク算出
        benchmarks = self._calculate_benchmarks()

        # ベンチマーク比較
        comparisons = self._compare_to_benchmarks(benchmarks)

        # 異常相関検出
        anomaly_correlations = self._detect_anomaly_correlations()

        # トップリスク集約
        top_risks = self._aggregate_top_risks()

        logger.info(
            "クロス企業分析完了: companies={}, industries={}, anomalies={}",
            len(self._profiles),
            len(industries),
            len(anomaly_correlations),
        )

        return CrossCompanyResult(
            total_companies=len(self._profiles),
            industries=industries,
            benchmarks=benchmarks,
            comparisons=comparisons,
            anomaly_correlations=anomaly_correlations,
            top_risks=top_risks,
        )

    def _calculate_benchmarks(self) -> list[IndustryBenchmark]:
        """業種別ベンチマークを算出"""
        benchmarks: list[IndustryBenchmark] = []

        # 業種ごとにグループ化
        industry_groups: dict[str, list[CompanyRiskProfile]] = {}
        for profile in self._profiles:
            industry_groups.setdefault(profile.industry, []).append(profile)

        for industry, profiles in industry_groups.items():
            # カテゴリ一覧を収集
            categories: set[str] = set()
            for p in profiles:
                categories.update(p.risk_scores.keys())

            for category in categories:
                scores = [
                    p.risk_scores[category]
                    for p in profiles
                    if category in p.risk_scores
                ]
                if not scores:
                    continue

                avg = sum(scores) / len(scores)
                sorted_scores = sorted(scores)
                n = len(sorted_scores)
                median = (
                    sorted_scores[n // 2]
                    if n % 2 == 1
                    else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
                )
                variance = (
                    sum((s - avg) ** 2 for s in scores) / len(scores)
                    if len(scores) > 0
                    else 0
                )
                std_dev = variance**0.5

                benchmarks.append(
                    IndustryBenchmark(
                        industry=industry,
                        category=category,
                        avg_score=round(avg, 2),
                        median_score=round(median, 2),
                        std_dev=round(std_dev, 2),
                        min_score=round(min(scores), 2),
                        max_score=round(max(scores), 2),
                        sample_size=len(scores),
                    )
                )

        return benchmarks

    def _compare_to_benchmarks(
        self, benchmarks: list[IndustryBenchmark]
    ) -> list[BenchmarkComparison]:
        """各企業をベンチマークと比較"""
        comparisons: list[BenchmarkComparison] = []

        # ベンチマーク索引
        bm_index: dict[tuple[str, str], IndustryBenchmark] = {}
        for bm in benchmarks:
            bm_index[(bm.industry, bm.category)] = bm

        for profile in self._profiles:
            for category, score in profile.risk_scores.items():
                bm: IndustryBenchmark | None = bm_index.get((profile.industry, category))
                if not bm:
                    continue

                # 偏差計算
                deviation = (
                    (score - bm.avg_score) / bm.std_dev
                    if bm.std_dev > 0
                    else 0.0
                )

                # パーセンタイル（簡易）
                percentile = self._calc_percentile(
                    score, profile.industry, category
                )

                # ステータス判定
                if deviation > 2.0:
                    status = "critical"
                elif deviation > 1.0:
                    status = "below_average"
                elif deviation < -1.0:
                    status = "above_average"
                else:
                    status = "average"

                comparisons.append(
                    BenchmarkComparison(
                        company_id=profile.company_id,
                        company_name=profile.company_name,
                        category=category,
                        company_score=round(score, 2),
                        benchmark_avg=bm.avg_score,
                        benchmark_median=bm.median_score,
                        percentile=round(percentile, 1),
                        deviation=round(deviation, 2),
                        status=status,
                    )
                )

        return comparisons

    def _calc_percentile(
        self, score: float, industry: str, category: str
    ) -> float:
        """スコアのパーセンタイルを計算"""
        scores = [
            p.risk_scores[category]
            for p in self._profiles
            if p.industry == industry and category in p.risk_scores
        ]
        if not scores:
            return 50.0

        # スコアが高い＝リスクが高い → パーセンタイルが高いほど悪い
        below = sum(1 for s in scores if s < score)
        return (below / len(scores)) * 100

    def _detect_anomaly_correlations(self) -> list[AnomalyCorrelation]:
        """企業間の異常相関を検出"""
        correlations: list[AnomalyCorrelation] = []

        # 全カテゴリ収集
        categories: set[str] = set()
        for p in self._profiles:
            categories.update(p.risk_scores.keys())

        # 企業ペアごとに相関を計算
        for i, p1 in enumerate(self._profiles):
            for p2 in self._profiles[i + 1:]:
                for category in categories:
                    if category not in p1.risk_scores or category not in p2.risk_scores:
                        continue

                    s1 = p1.risk_scores[category]
                    s2 = p2.risk_scores[category]

                    # 簡易相関: 両方高い→共起、片方高い→逆相関
                    threshold = 70.0
                    if s1 > threshold and s2 > threshold:
                        correlations.append(
                            AnomalyCorrelation(
                                company_a=p1.company_id,
                                company_b=p2.company_id,
                                category=category,
                                correlation=round(
                                    min(s1, s2) / max(s1, s2), 2
                                ),
                                pattern="co_occurrence",
                                description=(
                                    f"{p1.company_name}と{p2.company_name}の"
                                    f"'{category}'リスクが同時に高い"
                                ),
                            )
                        )
                    elif (s1 > threshold and s2 < 30) or (
                        s2 > threshold and s1 < 30
                    ):
                        correlations.append(
                            AnomalyCorrelation(
                                company_a=p1.company_id,
                                company_b=p2.company_id,
                                category=category,
                                correlation=-0.5,
                                pattern="inverse",
                                description=(
                                    f"{p1.company_name}と{p2.company_name}の"
                                    f"'{category}'リスクが逆方向"
                                ),
                            )
                        )

        return correlations

    def _aggregate_top_risks(self) -> list[dict[str, Any]]:
        """全企業のトップリスクを集約"""
        risk_items: list[dict[str, Any]] = []

        for profile in self._profiles:
            for category, score in profile.risk_scores.items():
                risk_items.append(
                    {
                        "company_id": profile.company_id,
                        "company_name": profile.company_name,
                        "industry": profile.industry,
                        "category": category,
                        "score": score,
                    }
                )

        # スコア降順でソートして上位を返す
        risk_items.sort(key=lambda x: x["score"], reverse=True)
        return risk_items[:20]

    def clear(self) -> None:
        """プロファイルをクリア"""
        self._profiles.clear()
