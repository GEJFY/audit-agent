"""予測リスクレポートテンプレート

3ヶ月先リスク予測データを構造化レポートフォーマットに変換。
信頼区間、カテゴリ別内訳、シナリオ分析セクションを含む。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.reports.risk_intelligence import RiskIntelligenceReport


@dataclass
class ForecastPoint:
    """予測ポイント"""

    month: str
    predicted_score: float
    lower_bound: float = 0.0
    upper_bound: float = 100.0


@dataclass
class CategoryForecast:
    """カテゴリ別予測"""

    category: str
    current_score: float
    predicted_score: float
    change: float = 0.0
    direction: str = "stable"  # up, down, stable


@dataclass
class ScenarioAnalysis:
    """シナリオ分析"""

    scenario: str  # best_case, base_case, worst_case
    label: str
    predicted_score: float
    probability: float = 0.0
    description: str = ""


@dataclass
class RiskForecastOutput:
    """予測リスクレポート出力"""

    title: str
    generated_at: str
    period: str
    current_score: float
    confidence: float
    forecast_points: list[ForecastPoint] = field(default_factory=list)
    category_forecasts: list[CategoryForecast] = field(default_factory=list)
    scenarios: list[ScenarioAnalysis] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    markdown: str = ""


class RiskForecastTemplate:
    """予測リスクレポートテンプレート

    RiskIntelligenceReportまたは生データから予測リスクレポートを生成。
    """

    @staticmethod
    def render_from_report(report: RiskIntelligenceReport) -> RiskForecastOutput:
        """RiskIntelligenceReportから予測レポートを生成"""
        forecast_section = report.get_section("forecast")
        forecast_data: dict[str, Any] = forecast_section.data if forecast_section else {}

        summary_section = report.get_section("summary")
        summary_data: dict[str, Any] = summary_section.data if summary_section else {}

        return RiskForecastTemplate.render(
            current_score=summary_data.get("current", report.overall_risk_score),
            predicted_scores=forecast_data.get("predicted", []),
            confidence=forecast_data.get("confidence", 0.0),
            category_forecasts=forecast_data.get("category_forecasts", {}),
            risk_factors=[f for f in report.key_findings if f],
            period_start=report.metadata.period_start,
            period_end=report.metadata.period_end,
            company_name=report.metadata.company_name,
        )

    @staticmethod
    def render(
        current_score: float,
        predicted_scores: list[dict[str, Any]] | None = None,
        confidence: float = 0.0,
        category_forecasts: dict[str, Any] | None = None,
        risk_factors: list[str] | None = None,
        period_start: str = "",
        period_end: str = "",
        company_name: str = "",
    ) -> RiskForecastOutput:
        """生データから予測リスクレポートを生成

        Args:
            current_score: 現在のリスクスコア
            predicted_scores: [{month, score, lower, upper}]
            confidence: 予測信頼度 (0.0-1.0)
            category_forecasts: {category: {current, predicted}}
            risk_factors: リスク要因リスト
            period_start: 期間開始
            period_end: 期間終了
            company_name: 企業名
        """
        now = datetime.now(tz=UTC).isoformat()
        period = f"{period_start} 〜 {period_end}" if period_start else ""

        # 予測ポイント構築
        forecast_points = RiskForecastTemplate._build_forecast_points(predicted_scores or [])

        # カテゴリ別予測構築
        cat_forecasts = RiskForecastTemplate._build_category_forecasts(category_forecasts or {})

        # シナリオ分析構築
        scenarios = RiskForecastTemplate._build_scenarios(current_score, forecast_points, confidence)

        # 推奨アクション生成
        recommendations = RiskForecastTemplate._generate_recommendations(
            current_score, forecast_points, confidence, cat_forecasts
        )

        # マークダウン生成
        markdown = RiskForecastTemplate._render_markdown(
            current_score=current_score,
            confidence=confidence,
            forecast_points=forecast_points,
            cat_forecasts=cat_forecasts,
            scenarios=scenarios,
            risk_factors=risk_factors or [],
            recommendations=recommendations,
            company_name=company_name,
            period=period,
        )

        return RiskForecastOutput(
            title=f"予測リスクレポート — {company_name or 'N/A'}",
            generated_at=now,
            period=period,
            current_score=current_score,
            confidence=confidence,
            forecast_points=forecast_points,
            category_forecasts=cat_forecasts,
            scenarios=scenarios,
            risk_factors=risk_factors or [],
            recommendations=recommendations,
            markdown=markdown,
        )

    @staticmethod
    def _build_forecast_points(predicted_scores: list[dict[str, Any]]) -> list[ForecastPoint]:
        """予測ポイントリストを構築"""
        points: list[ForecastPoint] = []
        for p in predicted_scores:
            score = float(p.get("score", 0.0))
            points.append(
                ForecastPoint(
                    month=str(p.get("month", "")),
                    predicted_score=score,
                    lower_bound=float(p.get("lower", max(0.0, score - 10.0))),
                    upper_bound=float(p.get("upper", min(100.0, score + 10.0))),
                )
            )
        return points

    @staticmethod
    def _build_category_forecasts(cat_data: dict[str, Any]) -> list[CategoryForecast]:
        """カテゴリ別予測を構築"""
        forecasts: list[CategoryForecast] = []
        for cat, data in cat_data.items():
            if not isinstance(data, dict):
                continue
            current = float(data.get("current", 0.0))
            predicted = float(data.get("predicted", 0.0))
            change = predicted - current
            direction = "up" if change > 1.0 else "down" if change < -1.0 else "stable"
            forecasts.append(
                CategoryForecast(
                    category=str(cat),
                    current_score=current,
                    predicted_score=predicted,
                    change=change,
                    direction=direction,
                )
            )
        # 変化量の絶対値が大きい順
        forecasts.sort(key=lambda f: abs(f.change), reverse=True)
        return forecasts

    @staticmethod
    def _build_scenarios(
        current_score: float,
        forecast_points: list[ForecastPoint],
        confidence: float,
    ) -> list[ScenarioAnalysis]:
        """シナリオ分析を構築"""
        if not forecast_points:
            return []

        last_predicted = forecast_points[-1].predicted_score
        uncertainty = max(5.0, (1.0 - confidence) * 30.0)

        return [
            ScenarioAnalysis(
                scenario="best_case",
                label="楽観シナリオ",
                predicted_score=max(0.0, last_predicted - uncertainty),
                probability=0.2,
                description="統制強化が予定通り進んだ場合",
            ),
            ScenarioAnalysis(
                scenario="base_case",
                label="基本シナリオ",
                predicted_score=last_predicted,
                probability=0.6,
                description="現在のトレンドが継続した場合",
            ),
            ScenarioAnalysis(
                scenario="worst_case",
                label="悲観シナリオ",
                predicted_score=min(100.0, last_predicted + uncertainty),
                probability=0.2,
                description="新たなリスク要因が顕在化した場合",
            ),
        ]

    @staticmethod
    def _generate_recommendations(
        current_score: float,
        forecast_points: list[ForecastPoint],
        confidence: float,
        cat_forecasts: list[CategoryForecast],
    ) -> list[str]:
        """推奨アクションを生成"""
        recs: list[str] = []

        # 信頼度ベース
        if confidence < 0.5:
            recs.append("予測モデルの信頼度が低いです。データ収集範囲の拡大を検討してください。")

        # トレンドベース
        if forecast_points:
            last = forecast_points[-1].predicted_score
            if last > current_score * 1.2:
                recs.append("リスクスコアの大幅な上昇が予測されています。予防的な統制強化を推奨します。")
            elif last < current_score * 0.8:
                recs.append("リスクスコアの改善が予測されています。現在の統制施策を継続してください。")

        # カテゴリベース
        worsening_cats = [f for f in cat_forecasts if f.direction == "up" and f.change > 10.0]
        if worsening_cats:
            cat_names = "、".join(f.category for f in worsening_cats[:3])
            recs.append(f"以下のカテゴリでリスク上昇が顕著です: {cat_names}")

        if not recs:
            recs.append("予測リスクは安定しています。定期モニタリングを継続してください。")

        return recs

    @staticmethod
    def _render_markdown(
        current_score: float,
        confidence: float,
        forecast_points: list[ForecastPoint],
        cat_forecasts: list[CategoryForecast],
        scenarios: list[ScenarioAnalysis],
        risk_factors: list[str],
        recommendations: list[str],
        company_name: str,
        period: str,
    ) -> str:
        """マークダウン形式でレンダリング"""
        lines: list[str] = []

        # ヘッダー
        lines.append(f"# 予測リスクレポート — {company_name or 'N/A'}")
        lines.append("")
        if period:
            lines.append(f"**対象期間**: {period}")
        lines.append(f"**現在リスクスコア**: {current_score:.1f}")
        lines.append(f"**予測信頼度**: {confidence:.0%}")
        lines.append("")

        # 3ヶ月予測
        if forecast_points:
            lines.append("## 3ヶ月リスク予測")
            lines.append("| 月 | 予測スコア | 下限 | 上限 |")
            lines.append("|----|----------|------|------|")
            for fp in forecast_points:
                lines.append(f"| {fp.month} | {fp.predicted_score:.1f} | {fp.lower_bound:.1f} | {fp.upper_bound:.1f} |")
            lines.append("")

        # カテゴリ別予測
        if cat_forecasts:
            lines.append("## カテゴリ別予測")
            lines.append("| カテゴリ | 現在 | 予測 | 変化 |")
            lines.append("|---------|------|------|------|")
            for cf in cat_forecasts:
                arrow = "↑" if cf.direction == "up" else "↓" if cf.direction == "down" else "→"
                lines.append(
                    f"| {cf.category} | {cf.current_score:.1f} "
                    f"| {cf.predicted_score:.1f} | {arrow}{abs(cf.change):.1f} |"
                )
            lines.append("")

        # シナリオ分析
        if scenarios:
            lines.append("## シナリオ分析")
            for s in scenarios:
                lines.append(
                    f"- **{s.label}** (確率 {s.probability:.0%}): スコア {s.predicted_score:.1f} — {s.description}"
                )
            lines.append("")

        # リスク要因
        if risk_factors:
            lines.append("## リスク要因")
            for f in risk_factors:
                lines.append(f"- {f}")
            lines.append("")

        # 推奨アクション
        if recommendations:
            lines.append("## 推奨アクション")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)
