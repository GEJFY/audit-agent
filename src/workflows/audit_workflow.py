"""監査側ワークフロー — Temporal Workflow定義

監査プロジェクトのライフサイクルを管理:
  init → planning → fieldwork → reporting → follow_up
"""

from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflows.activities import (
        AgentActivityInput,
        AgentActivityOutput,
        check_approval_status,
        run_auditor_agent,
        send_notification,
    )


@workflow.defn(name="AuditProjectWorkflow")
class AuditProjectWorkflow:
    """監査プロジェクト全体ワークフロー

    フェーズ遷移:
    1. planning: リスク評価 → 監査計画策定
    2. fieldwork: データ収集 → 統制テスト → 異常検知
    3. reporting: 指摘事項整理 → 報告書生成
    4. follow_up: 改善措置追跡
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._current_phase: str = "init"
        self._is_cancelled: bool = False
        self._approval_pending: bool = False

    @workflow.run  # type: ignore[misc]
    async def run(
        self,
        project_id: str,
        tenant_id: str,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """ワークフローメインループ"""
        self._state = initial_state or {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "current_phase": "init",
        }
        self._state["project_id"] = project_id
        self._state["tenant_id"] = tenant_id

        workflow.logger.info(f"監査ワークフロー開始: project={project_id}")

        # Phase 1: Planning
        self._current_phase = "planning"
        self._state["current_phase"] = "planning"

        plan_result = await self._run_agent("auditor_planner", tenant_id)
        if not plan_result.success:
            return self._error_result("計画策定失敗", plan_result.error)
        self._state = plan_result.updated_state

        # Human-in-the-Loop: 計画承認待ち
        if self._state.get("requires_approval"):
            approved = await self._wait_for_approval(tenant_id)
            if not approved:
                return self._error_result("計画が却下されました")

        # Phase 2: Fieldwork
        self._current_phase = "fieldwork"
        self._state["current_phase"] = "fieldwork"

        # データ収集
        data_result = await self._run_agent("auditor_data_collector", tenant_id)
        if data_result.success:
            self._state = data_result.updated_state

        # 統制テスト
        test_result = await self._run_agent("auditor_controls_tester", tenant_id)
        if test_result.success:
            self._state = test_result.updated_state

        # 異常検知
        anomaly_result = await self._run_agent("auditor_anomaly_detective", tenant_id)
        if anomaly_result.success:
            self._state = anomaly_result.updated_state

        # 知識検索（質問があれば）
        if self._state.get("pending_questions"):
            knowledge_result = await self._run_agent("auditor_knowledge", tenant_id)
            if knowledge_result.success:
                self._state = knowledge_result.updated_state

        # Phase 3: Reporting
        self._current_phase = "reporting"
        self._state["current_phase"] = "reporting"

        report_result = await self._run_agent("auditor_report_writer", tenant_id)
        if report_result.success:
            self._state = report_result.updated_state

        # 報告書承認待ち
        if self._state.get("requires_approval"):
            approved = await self._wait_for_approval(tenant_id)
            if not approved:
                return self._error_result("報告書が却下されました")

        # Phase 4: Follow-up
        self._current_phase = "follow_up"
        self._state["current_phase"] = "follow_up"

        followup_result = await self._run_agent("auditor_follow_up", tenant_id)
        if followup_result.success:
            self._state = followup_result.updated_state

        # 完了通知
        await workflow.execute_activity(
            send_notification,
            args=[tenant_id, f"監査プロジェクト {project_id} が完了しました"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        workflow.logger.info(f"監査ワークフロー完了: project={project_id}")
        self._state["workflow_status"] = "completed"
        return self._state

    async def _run_agent(self, agent_name: str, tenant_id: str) -> AgentActivityOutput:
        """Agent Activityを実行"""
        return await workflow.execute_activity(
            run_auditor_agent,
            arg=AgentActivityInput(
                agent_name=agent_name,
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )

    async def _wait_for_approval(self, tenant_id: str) -> bool:
        """Human-in-the-Loop承認待ち（ポーリング）"""
        self._approval_pending = True
        decision_id = self._state.get("approval_context", {}).get("decision_id", "")

        workflow.logger.info(f"承認待ち開始: decision={decision_id}")

        # 通知送信
        await workflow.execute_activity(
            send_notification,
            args=[tenant_id, "承認リクエストがあります。承認キューを確認してください。"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 最大7日間ポーリング（30秒間隔）
        for _ in range(20160):  # 7日 * 24h * 60min * 2 (30秒)
            result = await workflow.execute_activity(
                check_approval_status,
                args=[tenant_id, decision_id],
                start_to_close_timeout=timedelta(seconds=30),
            )

            status = result.get("status", "pending")
            if status == "approved":
                self._approval_pending = False
                self._state["requires_approval"] = False
                return True
            elif status == "rejected":
                self._approval_pending = False
                return False

            await workflow.sleep(timedelta(seconds=30))

        # タイムアウト
        self._approval_pending = False
        return False

    def _error_result(self, message: str, detail: str | None = None) -> dict[str, Any]:
        """エラー結果を生成"""
        self._state["workflow_status"] = "error"
        self._state["workflow_error"] = message
        if detail:
            self._state["workflow_error_detail"] = detail
        return self._state

    @workflow.query  # type: ignore[misc]
    def get_current_phase(self) -> str:
        """現在フェーズを返す"""
        return self._current_phase

    @workflow.query  # type: ignore[misc]
    def get_state(self) -> dict[str, Any]:
        """現在ステートを返す"""
        return self._state

    @workflow.signal  # type: ignore[misc]
    async def cancel_workflow(self) -> None:
        """ワークフローキャンセル"""
        self._is_cancelled = True
        workflow.logger.info("ワークフローキャンセルリクエスト受信")

    @workflow.signal  # type: ignore[misc]
    async def approve(self) -> None:
        """外部からの承認シグナル"""
        self._state["requires_approval"] = False
        self._approval_pending = False
