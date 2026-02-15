"""Controls Monitor Agent — 統制状態リアルタイムモニタリング（DB連携）"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState
from src.db.models.auditee import ControlsStatus, RiskAlert
from src.db.models.auditor import RCM, TestResult
from src.db.session import get_session


class ControlsMonitorAgent(BaseAuditAgent[AuditeeState]):
    """統制モニタリングAgent — RCM統制ごとの実施率・逸脱率をリアルタイム集計

    DBから統制実施データを取得し、スコアカードを計算。
    不備検出時はRiskAlertを自動生成してエスカレーション。
    """

    # 閾値デフォルト値
    DEFAULT_GREEN_THRESHOLD = 95.0  # 実施率95%以上 = green
    DEFAULT_YELLOW_THRESHOLD = 85.0  # 実施率85%以上 = yellow

    @property
    def agent_name(self) -> str:
        return "auditee_controls_monitor"

    @property
    def agent_description(self) -> str:
        return "統制モニタリング — 実施率・逸脱率リアルタイム集計・スコアカード・不備自己検出"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """統制状態を集計・評価"""
        logger.info("Controls Monitor: 統制モニタリング開始")

        controls_data = await self._collect_controls_data(state)
        scorecard = self._calculate_scorecard(controls_data)

        # DBに最新スコアカードを保存
        await self._persist_scorecard(state.tenant_id, scorecard)

        state.controls_status = scorecard

        # 不備の自己検出
        issues = [c for c in scorecard if c.get("status") == "red"]
        if issues:
            logger.warning("統制不備検出: {}件", len(issues))
            for issue in issues:
                alert = {
                    "type": "controls_deficiency",
                    "severity": "high",
                    "title": f"統制不備: {issue.get('control_name', '')}",
                    "description": (
                        f"実施率: {issue.get('execution_rate', 0)}%, 逸脱率: {issue.get('deviation_rate', 0)}%"
                    ),
                    "escalate_to_auditor": True,
                }
                state.risk_alerts.append(alert)
                await self._create_risk_alert(state.tenant_id, issue, alert)

        # トレンドサマリ
        trend_summary = self._analyze_trends(scorecard)

        self.record_decision(
            tenant_id=state.tenant_id,
            decision="controls_monitored",
            reasoning=(
                f"統制数: {len(scorecard)}, "
                f"green: {trend_summary['green']}, "
                f"yellow: {trend_summary['yellow']}, "
                f"red: {trend_summary['red']}"
            ),
            confidence=0.9 if not issues else 0.7,
            resource_type="controls_status",
            resource_id=state.tenant_id,
        )

        state.current_agent = self.agent_name
        logger.info("Controls Monitor: {}件の統制評価完了", len(scorecard))
        return state

    async def _collect_controls_data(self, state: AuditeeState) -> list[dict[str, Any]]:
        """統制実施データをRCM・TestResultからDB集計"""
        try:
            async for session in get_session():
                return await self._query_controls_data(session, state.tenant_id)
        except Exception as e:
            logger.error("統制データ収集エラー: {}", str(e))
            return []
        return []

    async def _query_controls_data(self, session: AsyncSession, tenant_id: str) -> list[dict[str, Any]]:
        """DBからRCMとTestResultを結合して統制実施状況を集計"""
        rcm_query = select(
            RCM.control_id,
            RCM.control_name,
            RCM.control_type,
            RCM.control_frequency,
            RCM.id,
        ).where(RCM.tenant_id == tenant_id)
        rcm_result = await session.execute(rcm_query)
        rcm_rows = rcm_result.fetchall()

        controls_data: list[dict[str, Any]] = []

        for row in rcm_rows:
            rcm_id = row[4]

            test_stats = await session.execute(
                select(
                    func.count(TestResult.id).label("total_tests"),
                    func.sum(TestResult.exceptions_found).label("total_exceptions"),
                    func.sum(TestResult.sample_tested).label("total_samples"),
                ).where(  # type: ignore[call-arg]
                    TestResult.rcm_id == str(rcm_id),
                    TestResult.tenant_id == tenant_id,
                )
            )
            stats = test_stats.fetchone()

            total_tests = stats[0] or 0 if stats else 0
            total_exceptions = stats[1] or 0 if stats else 0
            total_samples = stats[2] or 0 if stats else 0

            control_name = row[1] or ""
            category = self._infer_category(control_name, row[2] or "")

            controls_data.append(
                {
                    "control_id": row[0],
                    "control_name": control_name,
                    "category": category,
                    "control_type": row[2],
                    "frequency": row[3],
                    "executions": max(total_samples, total_tests),
                    "deviations": total_exceptions,
                    "rcm_id": str(rcm_id),
                }
            )

        # RCMが空の場合、ControlsStatusテーブルから既存データを取得
        if not controls_data:
            controls_data = await self._fallback_controls_status(session, tenant_id)

        return controls_data

    async def _fallback_controls_status(self, session: AsyncSession, tenant_id: str) -> list[dict[str, Any]]:
        """ControlsStatusテーブルからフォールバック取得"""
        result = await session.execute(select(ControlsStatus).where(ControlsStatus.tenant_id == tenant_id))
        rows = result.scalars().all()
        return [
            {
                "control_id": r.control_id,
                "control_name": r.control_name,
                "category": r.category,
                "executions": int(r.execution_rate),
                "deviations": int(r.deviation_rate),
            }
            for r in rows
        ]

    def _infer_category(self, control_name: str, control_type: str) -> str:
        """統制名・タイプからカテゴリを推定"""
        name_lower = control_name.lower()
        if any(kw in name_lower for kw in ("承認", "approval", "決裁")):
            return "approval"
        elif any(kw in name_lower for kw in ("アクセス", "access", "権限")):
            return "access"
        elif any(kw in name_lower for kw in ("取引", "transaction", "仕訳")):
            return "transaction"
        elif any(kw in name_lower for kw in ("it", "システム", "バックアップ")):
            return "it_general"
        elif any(kw in name_lower for kw in ("報告", "report", "レポート")):
            return "reporting"
        return "other"

    def _calculate_scorecard(self, controls_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """スコアカード計算"""
        scorecard: list[dict[str, Any]] = []

        for control in controls_data:
            executions = control.get("executions", 0)
            deviations = control.get("deviations", 0)
            execution_rate = ((executions - deviations) / max(executions, 1)) * 100
            deviation_rate = (deviations / max(executions, 1)) * 100

            if execution_rate >= self.DEFAULT_GREEN_THRESHOLD:
                status = "green"
            elif execution_rate >= self.DEFAULT_YELLOW_THRESHOLD:
                status = "yellow"
            else:
                status = "red"

            scorecard.append(
                {
                    **control,
                    "execution_rate": round(execution_rate, 1),
                    "deviation_rate": round(deviation_rate, 1),
                    "status": status,
                }
            )

        return scorecard

    def _analyze_trends(self, scorecard: list[dict[str, Any]]) -> dict[str, int]:
        """スコアカードのサマリを集計"""
        summary = {"green": 0, "yellow": 0, "red": 0}
        for card in scorecard:
            status = card.get("status", "")
            if status in summary:
                summary[status] += 1
        return summary

    async def _persist_scorecard(self, tenant_id: str, scorecard: list[dict[str, Any]]) -> None:
        """スコアカードをDBに保存（upsert）"""
        try:
            async for session in get_session():
                now = datetime.now(UTC).isoformat()
                for card in scorecard:
                    existing = await session.execute(
                        select(ControlsStatus).where(  # type: ignore[call-arg]
                            ControlsStatus.tenant_id == tenant_id,
                            ControlsStatus.control_id == card.get("control_id", ""),
                        )
                    )
                    row = existing.scalar_one_or_none()

                    if row:
                        row.execution_rate = card.get("execution_rate", 0)
                        row.deviation_rate = card.get("deviation_rate", 0)
                        row.status = card.get("status", "green")
                        row.last_checked_at = now
                        row.details = {
                            "executions": card.get("executions", 0),
                            "deviations": card.get("deviations", 0),
                        }
                    else:
                        new_status = ControlsStatus(
                            tenant_id=tenant_id,
                            control_id=card.get("control_id", ""),
                            control_name=card.get("control_name", ""),
                            category=card.get("category", "other"),
                            status=card.get("status", "green"),
                            execution_rate=card.get("execution_rate", 0),
                            deviation_rate=card.get("deviation_rate", 0),
                            last_checked_at=now,
                            details={
                                "executions": card.get("executions", 0),
                                "deviations": card.get("deviations", 0),
                            },
                        )
                        session.add(new_status)

                await session.commit()
                logger.debug("スコアカードDB保存完了: {}件", len(scorecard))
                return
        except Exception as e:
            logger.error("スコアカードDB保存エラー: {}", str(e))

    async def _create_risk_alert(
        self,
        tenant_id: str,
        issue: dict[str, Any],
        alert: dict[str, Any],
    ) -> None:
        """不備検出時にRiskAlertレコードを作成"""
        try:
            async for session in get_session():
                new_alert = RiskAlert(
                    tenant_id=tenant_id,
                    alert_type="controls_deficiency",
                    severity=alert.get("severity", "high"),
                    title=alert.get("title", ""),
                    description=alert.get("description", ""),
                    source="controls_monitor",
                    detection_data={
                        "control_id": issue.get("control_id", ""),
                        "execution_rate": issue.get("execution_rate", 0),
                        "deviation_rate": issue.get("deviation_rate", 0),
                    },
                    status="open",
                    escalated_to_auditor=alert.get("escalate_to_auditor", True),
                    escalated_at=datetime.now(UTC).isoformat(),
                )
                session.add(new_alert)
                await session.commit()
                return
        except Exception as e:
            logger.error("RiskAlert作成エラー: {}", str(e))
