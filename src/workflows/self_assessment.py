"""セルフアセスメント自動化ワークフロー

四半期ごとのセルフアセスメントを自動化:
  - アセスメント質問票の生成
  - 部門別回答の収集
  - 回答の品質評価・スコアリング
  - レビュー・承認フロー
  - レポート生成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflows.activities import (
        AgentActivityInput,
        AgentActivityOutput,
        run_auditee_agent,
        run_auditor_agent,
        send_notification,
    )


@dataclass
class AssessmentConfig:
    """セルフアセスメント設定"""

    assessment_type: str = "quarterly"  # quarterly, annual, ad_hoc
    fiscal_year: int = 2026
    quarter: int = 1
    departments: list[str] = field(default_factory=lambda: ["finance", "purchasing", "it", "hr"])
    control_categories: list[str] = field(
        default_factory=lambda: ["access_control", "financial_process", "it_general", "compliance"]
    )
    auto_score: bool = True
    require_approval: bool = True
    approval_timeout_days: int = 7


@workflow.defn(name="SelfAssessmentWorkflow")
class SelfAssessmentWorkflow:
    """四半期セルフアセスメント自動化ワークフロー

    フェーズ:
    1. 準備: 質問票生成、対象部門通知
    2. 回答収集: 部門別に回答を収集（並列）
    3. 評価: AI品質評価 + スコアリング
    4. レビュー: 統括部門の承認
    5. 報告: レポート生成・配信
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._approved: bool = False
        self._rejection_reason: str = ""

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        config_dict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """セルフアセスメント実行"""
        config = self._parse_config(config_dict)

        self._state = {
            "tenant_id": tenant_id,
            "assessment_type": config.assessment_type,
            "fiscal_year": config.fiscal_year,
            "quarter": config.quarter,
            "departments": config.departments,
            "control_categories": config.control_categories,
            "current_phase": "preparation",
            "department_results": {},
            "overall_score": 0.0,
        }

        workflow.logger.info(f"セルフアセスメント開始: tenant={tenant_id}, FY{config.fiscal_year} Q{config.quarter}")

        # Phase 1: 準備 — 質問票生成
        self._state["current_phase"] = "preparation"
        prep_result = await self._run_auditor_agent("auditor_planner", tenant_id)
        if prep_result.success:
            self._state.update(prep_result.updated_state)

        # 部門への通知
        await workflow.execute_activity(
            send_notification,
            args=[
                tenant_id,
                f"セルフアセスメント（FY{config.fiscal_year} Q{config.quarter}）が開始されました。"
                f"対象部門: {', '.join(config.departments)}",
            ],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Phase 2: 回答収集 — 部門別に順次実行
        self._state["current_phase"] = "collection"
        for dept in config.departments:
            dept_state = {
                **self._state,
                "department": dept,
                "current_phase": "responding",
            }

            # 被監査側エージェントで回答準備
            dept_result = await workflow.execute_activity(
                run_auditee_agent,
                arg=AgentActivityInput(
                    agent_name="auditee_prep",
                    state_dict=dept_state,
                    tenant_id=tenant_id,
                ),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=workflow.RetryPolicy(  # type: ignore[attr-defined]
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=5),
                ),
            )

            if dept_result.success:
                self._state["department_results"][dept] = dept_result.updated_state
            else:
                self._state["department_results"][dept] = {
                    "status": "error",
                    "error": dept_result.error,
                }

        # Phase 3: 評価 — AI品質評価+スコアリング
        self._state["current_phase"] = "evaluation"
        if config.auto_score:
            eval_result = await self._run_auditor_agent("auditor_controls_tester", tenant_id)
            if eval_result.success:
                self._state.update(eval_result.updated_state)

            # 全体スコア算出
            scores = []
            for _dept, result in self._state["department_results"].items():
                if isinstance(result, dict) and result.get("score"):
                    scores.append(result["score"])
            if scores:
                self._state["overall_score"] = sum(scores) / len(scores)

        # Phase 4: レビュー・承認
        self._state["current_phase"] = "review"
        if config.require_approval:
            await workflow.execute_activity(
                send_notification,
                args=[
                    tenant_id,
                    f"セルフアセスメント結果のレビュー・承認が必要です。全体スコア: {self._state['overall_score']:.1f}",
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )

            try:
                await workflow.wait_condition(
                    lambda: self._approved or bool(self._rejection_reason),
                    timeout=timedelta(days=config.approval_timeout_days),
                )
            except TimeoutError:
                workflow.logger.warning("セルフアセスメント承認タイムアウト")
                self._state["workflow_status"] = "approval_timeout"
                return self._state

            if self._rejection_reason:
                self._state["workflow_status"] = "rejected"
                self._state["rejection_reason"] = self._rejection_reason
                return self._state

        # Phase 5: レポート生成
        self._state["current_phase"] = "reporting"
        report_result = await self._run_auditor_agent("auditor_report_writer", tenant_id)
        if report_result.success:
            self._state.update(report_result.updated_state)

        self._state["workflow_status"] = "completed"
        self._state["current_phase"] = "completed"

        await workflow.execute_activity(
            send_notification,
            args=[
                tenant_id,
                f"セルフアセスメント（FY{config.fiscal_year} Q{config.quarter}）が完了しました。",
            ],
            start_to_close_timeout=timedelta(seconds=30),
        )

        workflow.logger.info(f"セルフアセスメント完了: tenant={tenant_id}")
        return self._state

    async def _run_auditor_agent(self, agent_name: str, tenant_id: str) -> AgentActivityOutput:
        """監査側エージェント実行"""
        return await workflow.execute_activity(  # type: ignore[call-overload]
            run_auditor_agent,
            arg=AgentActivityInput(
                agent_name=agent_name,
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(  # type: ignore[attr-defined]
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
            ),
        )

    @workflow.signal
    async def approve(self) -> None:
        """承認シグナル"""
        self._approved = True

    @workflow.signal
    async def reject(self, reason: str = "") -> None:
        """却下シグナル"""
        self._rejection_reason = reason or "却下理由未記入"

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        """現在のステートを返す"""
        return self._state

    @workflow.query
    def get_progress(self) -> dict[str, Any]:
        """進捗情報を返す"""
        completed_depts = sum(
            1
            for result in self._state.get("department_results", {}).values()
            if isinstance(result, dict) and result.get("status") != "error"
        )
        total_depts = len(self._state.get("departments", []))

        return {
            "current_phase": self._state.get("current_phase", "unknown"),
            "departments_completed": completed_depts,
            "departments_total": total_depts,
            "overall_score": self._state.get("overall_score", 0.0),
            "workflow_status": self._state.get("workflow_status", "in_progress"),
        }

    @staticmethod
    def _parse_config(config_dict: dict[str, Any] | None) -> AssessmentConfig:
        """設定辞書をAssessmentConfigに変換"""
        if not config_dict:
            return AssessmentConfig()
        return AssessmentConfig(
            assessment_type=config_dict.get("assessment_type", "quarterly"),
            fiscal_year=config_dict.get("fiscal_year", 2026),
            quarter=config_dict.get("quarter", 1),
            departments=config_dict.get("departments", ["finance", "purchasing", "it", "hr"]),
            control_categories=config_dict.get(
                "control_categories",
                ["access_control", "financial_process", "it_general", "compliance"],
            ),
            auto_score=config_dict.get("auto_score", True),
            require_approval=config_dict.get("require_approval", True),
            approval_timeout_days=config_dict.get("approval_timeout_days", 7),
        )
