"""監査委員会向けエグゼクティブサマリーテンプレート

RiskIntelligenceReportからボード向けフォーマットのサマリーを生成。
リスクヒートマップ、KPIテーブル、アクションアイテムを含む。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.reports.risk_intelligence import RiskIntelligenceReport


@dataclass
class KPIItem:
    """KPI指標"""

    label: str
    value: str
    trend: str = "stable"  # improving, stable, worsening
    target: str = ""


@dataclass
class HeatmapCell:
    """リスクヒートマップセル"""

    category: str
    score: float
    level: str  # low, medium, high, critical
    trend: str = "stable"


@dataclass
class ActionItem:
    """アクションアイテム"""

    title: str
    priority: str  # high, medium, low
    owner: str = ""
    due_date: str = ""
    status: str = "open"


@dataclass
class ExecutiveSummaryOutput:
    """エグゼクティブサマリー出力"""

    title: str
    generated_at: str
    period: str
    overall_score: float
    overall_level: str
    risk_trend: str
    kpis: list[KPIItem] = field(default_factory=list)
    heatmap: list[HeatmapCell] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    markdown: str = ""


class ExecutiveSummaryTemplate:
    """監査委員会向けエグゼクティブサマリーテンプレート

    RiskIntelligenceReportを受け取り、ボード向けフォーマットに整形。
    """

    @staticmethod
    def render(
        report: RiskIntelligenceReport,
        extra_kpis: list[dict[str, str]] | None = None,
    ) -> ExecutiveSummaryOutput:
        """レポートからエグゼクティブサマリーを生成

        Args:
            report: リスクインテリジェンスレポート
            extra_kpis: 追加KPI [{label, value, trend, target}]
        """
        now = datetime.now(tz=UTC).isoformat()
        period = f"{report.metadata.period_start} 〜 {report.metadata.period_end}"

        # リスクヒートマップ構築
        heatmap = ExecutiveSummaryTemplate._build_heatmap(report)

        # KPI構築
        kpis = ExecutiveSummaryTemplate._build_kpis(report, extra_kpis)

        # アクションアイテム構築
        action_items = ExecutiveSummaryTemplate._build_action_items(report)

        # マークダウン生成
        overall_level = ExecutiveSummaryTemplate._score_to_level(report.overall_risk_score)
        markdown = ExecutiveSummaryTemplate._render_markdown(
            report=report,
            heatmap=heatmap,
            kpis=kpis,
            action_items=action_items,
            overall_level=overall_level,
            period=period,
        )

        return ExecutiveSummaryOutput(
            title=f"エグゼクティブサマリー — {report.metadata.company_name or 'N/A'}",
            generated_at=now,
            period=period,
            overall_score=report.overall_risk_score,
            overall_level=overall_level,
            risk_trend=report.risk_trend,
            kpis=kpis,
            heatmap=heatmap,
            key_findings=report.key_findings,
            action_items=action_items,
            recommendations=report.recommendations,
            markdown=markdown,
        )

    @staticmethod
    def _build_heatmap(report: RiskIntelligenceReport) -> list[HeatmapCell]:
        """リスクヒートマップデータを構築"""
        heatmap: list[HeatmapCell] = []

        risk_overview = report.get_section("risk_overview")
        if not risk_overview or not risk_overview.data:
            return heatmap

        for category, score in risk_overview.data.items():
            if not isinstance(score, int | float):
                continue
            level = ExecutiveSummaryTemplate._score_to_level(float(score))
            heatmap.append(
                HeatmapCell(
                    category=str(category),
                    score=float(score),
                    level=level,
                )
            )

        # スコア降順でソート
        heatmap.sort(key=lambda c: c.score, reverse=True)
        return heatmap

    @staticmethod
    def _build_kpis(
        report: RiskIntelligenceReport,
        extra_kpis: list[dict[str, str]] | None = None,
    ) -> list[KPIItem]:
        """KPI指標を構築"""
        kpis: list[KPIItem] = [
            KPIItem(
                label="全体リスクスコア",
                value=f"{report.overall_risk_score:.1f}",
                trend=report.risk_trend,
            ),
            KPIItem(
                label="主要所見数",
                value=str(len(report.key_findings)),
            ),
            KPIItem(
                label="セクション数",
                value=str(report.section_count),
            ),
        ]

        # 予測セクションからKPI追加
        forecast_section = report.get_section("forecast")
        if forecast_section and forecast_section.data:
            predicted = forecast_section.data.get("predicted_score", None)
            if predicted is not None:
                kpis.append(
                    KPIItem(
                        label="予測リスクスコア（3ヶ月後）",
                        value=f"{predicted:.1f}",
                    )
                )

        # 追加KPI
        if extra_kpis:
            for kpi_data in extra_kpis:
                kpis.append(
                    KPIItem(
                        label=kpi_data.get("label", ""),
                        value=kpi_data.get("value", ""),
                        trend=kpi_data.get("trend", "stable"),
                        target=kpi_data.get("target", ""),
                    )
                )

        return kpis

    @staticmethod
    def _build_action_items(report: RiskIntelligenceReport) -> list[ActionItem]:
        """推奨アクションからアクションアイテムを生成"""
        items: list[ActionItem] = []
        for i, rec in enumerate(report.recommendations):
            # リスクスコアに基づく優先度
            priority = "high" if report.overall_risk_score >= 60 else "medium"
            if i > 2:
                priority = "low"

            items.append(
                ActionItem(
                    title=rec,
                    priority=priority,
                )
            )
        return items

    @staticmethod
    def _render_markdown(
        report: RiskIntelligenceReport,
        heatmap: list[HeatmapCell],
        kpis: list[KPIItem],
        action_items: list[ActionItem],
        overall_level: str,
        period: str,
    ) -> str:
        """マークダウン形式でレンダリング"""
        lines: list[str] = []

        # ヘッダー
        lines.append(f"# エグゼクティブサマリー — {report.metadata.company_name or 'N/A'}")
        lines.append("")
        lines.append(f"**対象期間**: {period}")
        lines.append(f"**全体リスク**: {report.overall_risk_score:.1f} ({overall_level})")
        trend_label = {"improving": "改善傾向", "stable": "安定", "worsening": "悪化傾向"}.get(
            report.risk_trend, report.risk_trend
        )
        lines.append(f"**トレンド**: {trend_label}")
        lines.append("")

        # KPIテーブル
        lines.append("## KPI指標")
        lines.append("| 指標 | 値 | トレンド |")
        lines.append("|------|-----|---------|")
        for kpi in kpis:
            lines.append(f"| {kpi.label} | {kpi.value} | {kpi.trend} |")
        lines.append("")

        # リスクヒートマップ
        if heatmap:
            lines.append("## リスクヒートマップ")
            lines.append("| カテゴリ | スコア | レベル |")
            lines.append("|---------|--------|--------|")
            for cell in heatmap:
                lines.append(f"| {cell.category} | {cell.score:.1f} | {cell.level} |")
            lines.append("")

        # 主要所見
        if report.key_findings:
            lines.append("## 主要所見")
            for i, finding in enumerate(report.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")

        # アクションアイテム
        if action_items:
            lines.append("## アクションアイテム")
            for item in action_items:
                lines.append(f"- [{item.priority}] {item.title}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _score_to_level(score: float) -> str:
        """スコアをレベル文字列に変換"""
        if score >= 80:
            return "critical"
        if score >= 60:
            return "high"
        if score >= 40:
            return "medium"
        return "low"
