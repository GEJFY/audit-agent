"""リスクインテリジェンスレポート自動生成

監査委員会向けリスクインテリジェンスレポートを自動生成。
予測リスク・クロス分析・プロセスマイニング結果を統合。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger


@dataclass
class ReportSection:
    """レポートセクション"""

    title: str
    content: str
    section_type: str  # summary, risk_overview, forecast, benchmark, process, recommendation
    priority: int = 0  # 表示順（低い＝先頭）
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportMetadata:
    """レポートメタデータ"""

    report_id: str
    title: str
    report_type: str  # executive_summary, risk_forecast, audit_committee
    generated_at: str = ""
    period_start: str = ""
    period_end: str = ""
    company_id: str = ""
    company_name: str = ""
    industry: str = ""
    region: str = "JP"
    version: str = "1.0"


@dataclass
class RiskIntelligenceReport:
    """リスクインテリジェンスレポート"""

    metadata: ReportMetadata
    sections: list[ReportSection]
    overall_risk_score: float = 0.0
    risk_trend: str = "stable"  # improving, stable, worsening
    key_findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def section_count(self) -> int:
        return len(self.sections)

    def get_section(self, section_type: str) -> ReportSection | None:
        """セクションタイプで検索"""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None

    def to_markdown(self) -> str:
        """マークダウン形式で出力"""
        lines = [
            f"# {self.metadata.title}",
            "",
            f"**レポートID**: {self.metadata.report_id}",
            f"**生成日時**: {self.metadata.generated_at}",
            f"**対象期間**: {self.metadata.period_start} 〜 {self.metadata.period_end}",
            f"**全体リスクスコア**: {self.overall_risk_score}",
            f"**リスクトレンド**: {self.risk_trend}",
            "",
        ]

        if self.key_findings:
            lines.append("## 主要所見")
            for i, finding in enumerate(self.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")

        for section in sorted(self.sections, key=lambda s: s.priority):
            lines.append(f"## {section.title}")
            lines.append(section.content)
            lines.append("")

        if self.recommendations:
            lines.append("## 推奨アクション")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)


class RiskIntelligenceReportGenerator:
    """リスクインテリジェンスレポート生成エンジン

    各種分析結果を統合し、監査委員会向けレポートを自動生成。
    LLM統合は将来的に追加予定（現在はテンプレートベース）。
    """

    def __init__(self, company_id: str = "", company_name: str = "") -> None:
        self._company_id = company_id
        self._company_name = company_name

    def generate_executive_summary(
        self,
        risk_data: dict[str, Any],
        period_start: str = "",
        period_end: str = "",
    ) -> RiskIntelligenceReport:
        """監査委員会向けエグゼクティブサマリーを生成

        Args:
            risk_data: {
                "overall_score": float,
                "risk_trend": str,
                "category_scores": {category: score},
                "top_findings": [str],
                "forecast": {"predicted_score": float, "confidence": float},
                "benchmark": {"percentile": float, "industry_avg": float},
                "process_issues": [str],
            }
        """
        now = datetime.now(tz=UTC).isoformat()
        report_id = f"RPT-{now[:10].replace('-', '')}"

        sections: list[ReportSection] = []

        # 1. サマリーセクション
        overall_score = risk_data.get("overall_score", 0.0)
        risk_trend = risk_data.get("risk_trend", "stable")
        sections.append(self._build_summary_section(overall_score, risk_trend))

        # 2. リスク概観セクション
        category_scores = risk_data.get("category_scores", {})
        if category_scores:
            sections.append(self._build_risk_overview_section(category_scores))

        # 3. 予測リスクセクション
        forecast = risk_data.get("forecast", {})
        if forecast:
            sections.append(self._build_forecast_section(forecast))

        # 4. ベンチマークセクション
        benchmark = risk_data.get("benchmark", {})
        if benchmark:
            sections.append(self._build_benchmark_section(benchmark))

        # 5. プロセス分析セクション
        process_issues = risk_data.get("process_issues", [])
        if process_issues:
            sections.append(self._build_process_section(process_issues))

        # 6. 推奨アクション
        recommendations = self._generate_recommendations(risk_data)

        # 主要所見
        key_findings = risk_data.get("top_findings", [])

        metadata = ReportMetadata(
            report_id=report_id,
            title="リスクインテリジェンスレポート — エグゼクティブサマリー",
            report_type="executive_summary",
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            company_id=self._company_id,
            company_name=self._company_name,
        )

        logger.info(
            "レポート生成完了: id={}, sections={}, findings={}",
            report_id,
            len(sections),
            len(key_findings),
        )

        return RiskIntelligenceReport(
            metadata=metadata,
            sections=sections,
            overall_risk_score=overall_score,
            risk_trend=risk_trend,
            key_findings=key_findings,
            recommendations=recommendations,
        )

    def generate_risk_forecast_report(
        self,
        forecast_data: dict[str, Any],
        period_start: str = "",
        period_end: str = "",
    ) -> RiskIntelligenceReport:
        """予測リスクレポートを生成

        Args:
            forecast_data: {
                "current_score": float,
                "predicted_scores": [{month: str, score: float}],
                "risk_factors": [str],
                "confidence": float,
                "category_forecasts": {category: {current: float, predicted: float}},
            }
        """
        now = datetime.now(tz=UTC).isoformat()
        report_id = f"RPT-FC-{now[:10].replace('-', '')}"

        sections: list[ReportSection] = []

        # 現在 vs 予測
        current = forecast_data.get("current_score", 0.0)
        predicted = forecast_data.get("predicted_scores", [])
        confidence = forecast_data.get("confidence", 0.0)

        sections.append(
            ReportSection(
                title="予測サマリー",
                content=self._format_forecast_summary(current, predicted, confidence),
                section_type="summary",
                priority=0,
                data={"current": current, "predicted": predicted},
            )
        )

        # カテゴリ別予測
        cat_forecasts = forecast_data.get("category_forecasts", {})
        if cat_forecasts:
            sections.append(
                ReportSection(
                    title="カテゴリ別リスク予測",
                    content=self._format_category_forecasts(cat_forecasts),
                    section_type="forecast",
                    priority=1,
                    data=cat_forecasts,
                )
            )

        # リスク要因
        risk_factors = forecast_data.get("risk_factors", [])
        if risk_factors:
            sections.append(
                ReportSection(
                    title="主要リスク要因",
                    content="\n".join(f"- {f}" for f in risk_factors),
                    section_type="risk_overview",
                    priority=2,
                )
            )

        # トレンド判定
        trend = "stable"
        if predicted:
            last_predicted = predicted[-1].get("score", current)
            if last_predicted > current * 1.1:
                trend = "worsening"
            elif last_predicted < current * 0.9:
                trend = "improving"

        metadata = ReportMetadata(
            report_id=report_id,
            title="予測リスクレポート",
            report_type="risk_forecast",
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            company_id=self._company_id,
            company_name=self._company_name,
        )

        return RiskIntelligenceReport(
            metadata=metadata,
            sections=sections,
            overall_risk_score=current,
            risk_trend=trend,
            key_findings=[f"予測信頼度: {confidence:.0%}"],
            recommendations=self._generate_forecast_recommendations(forecast_data),
        )

    def _build_summary_section(self, overall_score: float, risk_trend: str) -> ReportSection:
        """サマリーセクション構築"""
        trend_label = {
            "improving": "改善傾向",
            "stable": "安定",
            "worsening": "悪化傾向",
        }.get(risk_trend, "不明")

        level = self._score_to_level(overall_score)

        content = f"全体リスクスコア: **{overall_score:.1f}** ({level})\nリスクトレンド: **{trend_label}**"

        return ReportSection(
            title="エグゼクティブサマリー",
            content=content,
            section_type="summary",
            priority=0,
            data={
                "overall_score": overall_score,
                "risk_trend": risk_trend,
                "level": level,
            },
        )

    def _build_risk_overview_section(self, category_scores: dict[str, float]) -> ReportSection:
        """リスク概観セクション構築"""
        lines = []
        for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
            level = self._score_to_level(score)
            lines.append(f"- **{category}**: {score:.1f} ({level})")

        return ReportSection(
            title="リスクカテゴリ別概観",
            content="\n".join(lines),
            section_type="risk_overview",
            priority=1,
            data=category_scores,
        )

    def _build_forecast_section(self, forecast: dict[str, Any]) -> ReportSection:
        """予測リスクセクション構築"""
        predicted = forecast.get("predicted_score", 0.0)
        confidence = forecast.get("confidence", 0.0)

        content = f"予測リスクスコア（3ヶ月後）: **{predicted:.1f}**\n予測信頼度: **{confidence:.0%}**"

        return ReportSection(
            title="予測リスク分析",
            content=content,
            section_type="forecast",
            priority=2,
            data=forecast,
        )

    def _build_benchmark_section(self, benchmark: dict[str, Any]) -> ReportSection:
        """ベンチマークセクション構築"""
        percentile = benchmark.get("percentile", 50.0)
        industry_avg = benchmark.get("industry_avg", 0.0)

        content = f"業種内パーセンタイル: **{percentile:.0f}%**\n業種平均: **{industry_avg:.1f}**"

        return ReportSection(
            title="業種ベンチマーク比較",
            content=content,
            section_type="benchmark",
            priority=3,
            data=benchmark,
        )

    def _build_process_section(self, issues: list[str]) -> ReportSection:
        """プロセス分析セクション構築"""
        content = "\n".join(f"- {issue}" for issue in issues)

        return ReportSection(
            title="プロセス分析所見",
            content=content,
            section_type="process",
            priority=4,
        )

    def _generate_recommendations(self, risk_data: dict[str, Any]) -> list[str]:
        """推奨アクションを生成"""
        recommendations: list[str] = []

        overall = risk_data.get("overall_score", 0.0)
        if overall >= 80:
            recommendations.append("全体リスクがクリティカルレベルです。緊急の是正計画策定を推奨します。")
        elif overall >= 60:
            recommendations.append("全体リスクが高水準です。重点カテゴリの統制強化を検討してください。")

        # カテゴリ別推奨
        category_scores = risk_data.get("category_scores", {})
        for cat, score in category_scores.items():
            if score >= 80:
                recommendations.append(f"'{cat}' カテゴリのリスクが非常に高い状態です。即座の対策を検討してください。")

        # 予測ベース推奨
        forecast = risk_data.get("forecast", {})
        predicted = forecast.get("predicted_score", 0.0)
        if predicted > overall * 1.2:
            recommendations.append("予測モデルにより今後のリスク上昇が見込まれています。予防的対策を検討してください。")

        # プロセスベース推奨
        process_issues = risk_data.get("process_issues", [])
        if len(process_issues) >= 3:
            recommendations.append(
                f"プロセス分析で{len(process_issues)}件の課題が検出されています。業務プロセスの見直しを推奨します。"
            )

        if not recommendations:
            recommendations.append("現状のリスクレベルは許容範囲内です。引き続きモニタリングを継続してください。")

        return recommendations

    def _generate_forecast_recommendations(self, forecast_data: dict[str, Any]) -> list[str]:
        """予測レポート用推奨アクション"""
        recommendations: list[str] = []
        confidence = forecast_data.get("confidence", 0.0)

        if confidence < 0.5:
            recommendations.append("予測モデルの信頼度が低いです。追加データの収集を検討してください。")

        cat_forecasts = forecast_data.get("category_forecasts", {})
        for cat, data in cat_forecasts.items():
            current = data.get("current", 0.0)
            predicted = data.get("predicted", 0.0)
            if predicted > current * 1.3:
                recommendations.append(f"'{cat}' カテゴリで30%以上のリスク上昇が予測されています。")

        if not recommendations:
            recommendations.append("予測リスクは安定しています。定期モニタリングを継続してください。")

        return recommendations

    def _format_forecast_summary(
        self,
        current: float,
        predicted: list[dict[str, Any]],
        confidence: float,
    ) -> str:
        """予測サマリーのフォーマット"""
        lines = [f"現在のリスクスコア: **{current:.1f}**"]

        if predicted:
            for p in predicted:
                month = p.get("month", "N/A")
                score = p.get("score", 0.0)
                lines.append(f"- {month}: {score:.1f}")

        lines.append(f"\n予測信頼度: **{confidence:.0%}**")
        return "\n".join(lines)

    def _format_category_forecasts(self, cat_forecasts: dict[str, Any]) -> str:
        """カテゴリ別予測のフォーマット"""
        lines = []
        for cat, data in cat_forecasts.items():
            current = data.get("current", 0.0)
            predicted = data.get("predicted", 0.0)
            diff = predicted - current
            arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            lines.append(f"- **{cat}**: {current:.1f} → {predicted:.1f} ({arrow}{abs(diff):.1f})")
        return "\n".join(lines)

    @staticmethod
    def _score_to_level(score: float) -> str:
        """スコアをリスクレベル文字列に変換"""
        if score >= 80:
            return "クリティカル"
        if score >= 60:
            return "高"
        if score >= 40:
            return "中"
        return "低"
