"""被監査側ワークフロー — Temporal Workflow定義

被監査側の日常モニタリングおよび監査対応を管理:
  - 質問受信→回答生成→承認→送信
  - 証跡検索→収集→送付
  - 統制モニタリング→アラート
  - リスク監視→エスカレーション
"""

from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflows.activities import (
        AgentActivityInput,
        AgentActivityOutput,
        run_auditee_agent,
        send_notification,
    )


@workflow.defn(name="AuditeeResponseWorkflow")
class AuditeeResponseWorkflow:
    """質問回答ワークフロー

    1. 質問受信→オーケストレーター
    2. 回答ドラフト生成
    3. 証跡検索
    4. 部門長承認
    5. 回答送信
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._approved: bool = False

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        questions: list[dict[str, Any]],
        department: str = "",
    ) -> dict[str, Any]:
        """回答ワークフロー実行"""
        self._state = {
            "tenant_id": tenant_id,
            "department": department,
            "incoming_questions": questions,
            "current_phase": "idle",
        }

        workflow.logger.info(f"回答ワークフロー開始: tenant={tenant_id}, 質問数={len(questions)}")

        # Step 1: オーケストレーション
        orch_result = await self._run_agent("auditee_orchestrator", tenant_id)
        if orch_result.success:
            self._state = orch_result.updated_state

        # Step 2: 回答ドラフト生成
        response_result = await self._run_agent("auditee_response", tenant_id)
        if response_result.success:
            self._state = response_result.updated_state

        # Step 3: 証跡検索（必要な場合）
        if self._state.get("evidence_queue"):
            evidence_result = await self._run_agent("auditee_evidence_search", tenant_id)
            if evidence_result.success:
                self._state = evidence_result.updated_state

        # Step 4: 承認待ち（低信頼度の場合）
        if self._state.get("requires_approval"):
            await workflow.execute_activity(
                send_notification,
                args=[tenant_id, "回答ドラフトのレビュー・承認が必要です"],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # 承認シグナル待ち（最大3日）
            try:
                await workflow.wait_condition(
                    lambda: self._approved,
                    timeout=timedelta(days=3),
                )
            except TimeoutError:
                workflow.logger.warning("承認タイムアウト")
                self._state["workflow_status"] = "approval_timeout"
                return self._state

        self._state["workflow_status"] = "completed"
        workflow.logger.info(f"回答ワークフロー完了: tenant={tenant_id}")
        return self._state

    async def _run_agent(self, agent_name: str, tenant_id: str) -> AgentActivityOutput:
        """Agent Activityを実行"""
        return await workflow.execute_activity(  # type: ignore[no-any-return,call-overload]
            run_auditee_agent,
            arg=AgentActivityInput(
                agent_name=agent_name,
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(  # type: ignore[attr-defined]
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
            ),
        )

    @workflow.signal
    async def approve_response(self) -> None:
        """承認シグナル"""
        self._approved = True

    @workflow.signal
    async def reject_response(self, reason: str = "") -> None:
        """却下シグナル"""
        self._state["rejection_reason"] = reason
        self._state["workflow_status"] = "rejected"

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        """現在ステートを返す"""
        return self._state


@workflow.defn(name="ControlsMonitoringWorkflow")
class ControlsMonitoringWorkflow:
    """統制モニタリング定期実行ワークフロー

    cron: 毎日1回実行
    統制状態を集計し、不備があればアラートを発行。
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    @workflow.run
    async def run(self, tenant_id: str) -> dict[str, Any]:
        """モニタリング実行"""
        self._state = {
            "tenant_id": tenant_id,
            "current_phase": "monitoring",
        }

        workflow.logger.info(f"統制モニタリング開始: tenant={tenant_id}")

        # 統制モニタリング実行
        monitor_result = await workflow.execute_activity(
            run_auditee_agent,
            arg=AgentActivityInput(
                agent_name="auditee_controls_monitor",
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=2),  # type: ignore[attr-defined]
        )

        if monitor_result.success:
            self._state = monitor_result.updated_state

            # 不備検出時は通知
            risk_alerts = self._state.get("risk_alerts", [])
            if risk_alerts:
                await workflow.execute_activity(
                    send_notification,
                    args=[
                        tenant_id,
                        f"統制不備検出: {len(risk_alerts)}件のアラートがあります",
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                )

        # リスクアラートAgent実行
        alert_result = await workflow.execute_activity(
            run_auditee_agent,
            arg=AgentActivityInput(
                agent_name="auditee_risk_alert",
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=workflow.RetryPolicy(maximum_attempts=2),  # type: ignore[attr-defined]
        )

        if alert_result.success:
            self._state = alert_result.updated_state

        self._state["workflow_status"] = "completed"
        workflow.logger.info(f"統制モニタリング完了: tenant={tenant_id}")
        return self._state

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        return self._state
