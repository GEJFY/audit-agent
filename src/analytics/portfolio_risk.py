"""ポートフォリオリスク集約 — 複数企業リスクのポートフォリオビュー

50社規模のリスクポートフォリオを集約し、
ヒートマップデータ・サマリー・アラートを生成。
"""

from dataclasses import dataclass, field

from loguru import logger


@dataclass
class CompanyRiskSummary:
    """企業リスクサマリー（ポートフォリオ用）"""

    company_id: str
    company_name: str
    industry: str
    region: str = "JP"
    overall_score: float = 0.0
    risk_level: str = "low"  # critical, high, medium, low
    category_scores: dict[str, float] = field(default_factory=dict)
    trend: str = "stable"  # improving, stable, worsening
    open_findings: int = 0


@dataclass
class HeatmapCell:
    """ヒートマップセル"""

    company_id: str
    company_name: str
    category: str
    score: float
    risk_level: str


@dataclass
class PortfolioAlert:
    """ポートフォリオアラート"""

    alert_type: str  # threshold_breach, trend_change, concentration_risk
    severity: str  # critical, high, medium, low
    description: str
    affected_companies: list[str] = field(default_factory=list)


@dataclass
class PortfolioSummary:
    """ポートフォリオサマリー"""

    total_companies: int
    avg_overall_score: float
    risk_distribution: dict[str, int]  # risk_level -> count
    industry_distribution: dict[str, int]  # industry -> count
    region_distribution: dict[str, int]  # region -> count
    heatmap: list[HeatmapCell]
    alerts: list[PortfolioAlert]
    top_risk_companies: list[CompanyRiskSummary]
    category_averages: dict[str, float]


class PortfolioRiskAggregator:
    """ポートフォリオリスク集約エンジン

    複数企業のリスクデータをポートフォリオとして集約し、
    ヒートマップ・アラート・サマリーを生成。
    """

    def __init__(
        self,
        critical_threshold: float = 80.0,
        high_threshold: float = 60.0,
        medium_threshold: float = 40.0,
        concentration_alert_pct: float = 0.3,
    ) -> None:
        self._companies: list[CompanyRiskSummary] = []
        self._critical_threshold = critical_threshold
        self._high_threshold = high_threshold
        self._medium_threshold = medium_threshold
        self._concentration_alert_pct = concentration_alert_pct

    def add_company(self, company: CompanyRiskSummary) -> None:
        """企業サマリー追加"""
        self._companies.append(company)

    def add_companies(self, companies: list[CompanyRiskSummary]) -> None:
        """企業サマリー一括追加"""
        self._companies.extend(companies)

    @property
    def companies(self) -> list[CompanyRiskSummary]:
        """登録済み企業"""
        return self._companies

    def aggregate(self) -> PortfolioSummary:
        """ポートフォリオ集約を実行"""
        if not self._companies:
            return PortfolioSummary(
                total_companies=0,
                avg_overall_score=0.0,
                risk_distribution={},
                industry_distribution={},
                region_distribution={},
                heatmap=[],
                alerts=[],
                top_risk_companies=[],
                category_averages={},
            )

        # リスクレベル分類
        for company in self._companies:
            company.risk_level = self._classify_risk_level(
                company.overall_score
            )

        # 分布計算
        risk_dist = self._calc_risk_distribution()
        industry_dist = self._calc_industry_distribution()
        region_dist = self._calc_region_distribution()

        # 全体平均
        avg_score = sum(c.overall_score for c in self._companies) / len(
            self._companies
        )

        # ヒートマップデータ
        heatmap = self._build_heatmap()

        # アラート生成
        alerts = self._generate_alerts(risk_dist)

        # トップリスク企業
        top_risk = sorted(
            self._companies,
            key=lambda c: c.overall_score,
            reverse=True,
        )[:10]

        # カテゴリ平均
        category_avgs = self._calc_category_averages()

        logger.info(
            "ポートフォリオ集約完了: companies={}, avg_score={:.1f}, alerts={}",
            len(self._companies),
            avg_score,
            len(alerts),
        )

        return PortfolioSummary(
            total_companies=len(self._companies),
            avg_overall_score=round(avg_score, 2),
            risk_distribution=risk_dist,
            industry_distribution=industry_dist,
            region_distribution=region_dist,
            heatmap=heatmap,
            alerts=alerts,
            top_risk_companies=top_risk,
            category_averages=category_avgs,
        )

    def _classify_risk_level(self, score: float) -> str:
        """スコアからリスクレベルを分類"""
        if score >= self._critical_threshold:
            return "critical"
        if score >= self._high_threshold:
            return "high"
        if score >= self._medium_threshold:
            return "medium"
        return "low"

    def _calc_risk_distribution(self) -> dict[str, int]:
        """リスクレベル分布"""
        dist: dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for company in self._companies:
            level = company.risk_level
            dist[level] = dist.get(level, 0) + 1
        return dist

    def _calc_industry_distribution(self) -> dict[str, int]:
        """業種分布"""
        dist: dict[str, int] = {}
        for company in self._companies:
            dist[company.industry] = dist.get(company.industry, 0) + 1
        return dist

    def _calc_region_distribution(self) -> dict[str, int]:
        """リージョン分布"""
        dist: dict[str, int] = {}
        for company in self._companies:
            dist[company.region] = dist.get(company.region, 0) + 1
        return dist

    def _build_heatmap(self) -> list[HeatmapCell]:
        """ヒートマップデータを構築"""
        cells: list[HeatmapCell] = []
        for company in self._companies:
            for category, score in company.category_scores.items():
                cells.append(
                    HeatmapCell(
                        company_id=company.company_id,
                        company_name=company.company_name,
                        category=category,
                        score=round(score, 2),
                        risk_level=self._classify_risk_level(score),
                    )
                )
        return cells

    def _generate_alerts(
        self, risk_dist: dict[str, int]
    ) -> list[PortfolioAlert]:
        """ポートフォリオアラートを生成"""
        alerts: list[PortfolioAlert] = []
        total = len(self._companies)

        # 閾値超過アラート
        critical_companies = [
            c for c in self._companies if c.risk_level == "critical"
        ]
        if critical_companies:
            alerts.append(
                PortfolioAlert(
                    alert_type="threshold_breach",
                    severity="critical",
                    description=(
                        f"{len(critical_companies)}社がクリティカルリスクレベル"
                    ),
                    affected_companies=[
                        c.company_id for c in critical_companies
                    ],
                )
            )

        # 集中リスクアラート（特定業種に高リスクが集中）
        industry_risk: dict[str, list[str]] = {}
        for c in self._companies:
            if c.risk_level in ("critical", "high"):
                industry_risk.setdefault(c.industry, []).append(
                    c.company_id
                )

        for industry, company_ids in industry_risk.items():
            if len(company_ids) / max(total, 1) >= self._concentration_alert_pct:
                alerts.append(
                    PortfolioAlert(
                        alert_type="concentration_risk",
                        severity="high",
                        description=(
                            f"'{industry}'業種に高リスク企業が集中"
                            f"（{len(company_ids)}/{total}社）"
                        ),
                        affected_companies=company_ids,
                    )
                )

        # トレンド悪化アラート
        worsening = [
            c for c in self._companies if c.trend == "worsening"
        ]
        if len(worsening) >= 3:
            alerts.append(
                PortfolioAlert(
                    alert_type="trend_change",
                    severity="medium",
                    description=(
                        f"{len(worsening)}社でリスクトレンドが悪化中"
                    ),
                    affected_companies=[c.company_id for c in worsening],
                )
            )

        return alerts

    def _calc_category_averages(self) -> dict[str, float]:
        """カテゴリ別平均スコア"""
        category_scores: dict[str, list[float]] = {}
        for company in self._companies:
            for category, score in company.category_scores.items():
                category_scores.setdefault(category, []).append(score)

        return {
            cat: round(sum(scores) / len(scores), 2)
            for cat, scores in category_scores.items()
        }

    def clear(self) -> None:
        """企業データをクリア"""
        self._companies.clear()
