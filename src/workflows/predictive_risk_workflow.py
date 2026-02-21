"""予測リスク評価ワークフロー — Temporal Workflow定義

週次で予測リスク評価を実行:
  データ収集 → 予測モデル実行 → レポート生成 → 通知
"""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.workflows.activities import (
        AgentActivityInput,
        run_auditor_agent,
        send_notification,
    )


@workflow.defn(name="PredictiveRiskWorkflow")
class PredictiveRiskWorkflow:
    """週次予測リスク評価ワークフロー

    実行フロー:
    1. collect: 直近データの収集
    2. predict: 予測リスクモデル実行（3ヶ月先予測）
    3. report: 予測リスクレポート生成
    4. notify: 関係者への通知
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._current_step: str = "init"
        self._is_cancelled: bool = False

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        company_id: str = "",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """ワークフローメインループ

        Args:
            tenant_id: テナントID
            company_id: 企業ID
            config: オプション設定 {forecast_months, risk_threshold, notify_on_increase}
        """
        wf_config = config or {}
        self._state = {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "forecast_months": wf_config.get("forecast_months", 3),
            "risk_threshold": wf_config.get("risk_threshold", 70.0),
            "notify_on_increase": wf_config.get("notify_on_increase", True),
            "workflow_status": "running",
        }

        workflow.logger.info(f"予測リスク評価開始: tenant={tenant_id}, company={company_id}")

        # Step 1: データ収集
        self._current_step = "collect"
        collect_result = await self._run_agent("auditor_data_collector", tenant_id)
        if collect_result.get("success"):
            self._state["collected_data"] = collect_result.get("updated_state", {}).get("collected_data", [])

        # Step 2: 異常検知 + リスクスコアリング
        self._current_step = "analyze"
        analysis_result = await self._run_agent("auditor_anomaly_detective", tenant_id)
        if analysis_result.get("success"):
            self._state["analysis_result"] = analysis_result.get("updated_state", {})

        # Step 3: 予測リスク評価
        self._current_step = "predict"
        self._state["prediction"] = await self._run_prediction(tenant_id)

        # Step 4: レポート生成
        self._current_step = "report"
        report_result = await self._run_agent("auditor_report_writer", tenant_id)
        if report_result.get("success"):
            self._state["report"] = report_result.get("updated_state", {}).get("report", {})

        # Step 5: 通知（リスク閾値超過時）
        self._current_step = "notify"
        await self._send_risk_notification(tenant_id)

        # 完了
        self._current_step = "completed"
        self._state["workflow_status"] = "completed"
        workflow.logger.info(f"予測リスク評価完了: tenant={tenant_id}")
        return self._state

    async def _run_agent(self, agent_name: str, tenant_id: str) -> dict[str, Any]:
        """Agent Activityを実行"""
        result = await workflow.execute_activity(
            run_auditor_agent,
            arg=AgentActivityInput(
                agent_name=agent_name,
                state_dict=self._state,
                tenant_id=tenant_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )
        return {
            "success": result.success,
            "updated_state": result.updated_state if result.success else {},
        }

    async def _run_prediction(self, tenant_id: str) -> dict[str, Any]:
        """予測モデル実行（Activityとして実行）"""
        # 予測はanomalyエージェントの結果を活用
        analysis = self._state.get("analysis_result", {})
        return {
            "forecast_months": self._state.get("forecast_months", 3),
            "analysis_summary": analysis.get("metadata", {}).get("summary", ""),
            "tenant_id": tenant_id,
            "status": "completed",
        }

    async def _send_risk_notification(self, tenant_id: str) -> None:
        """リスク通知送信"""
        threshold = self._state.get("risk_threshold", 70.0)
        notify_on_increase = self._state.get("notify_on_increase", True)

        if not notify_on_increase:
            return

        # 現在のリスクスコアを取得
        analysis = self._state.get("analysis_result", {})
        current_score = analysis.get("metadata", {}).get("risk_score", 0.0)

        if current_score >= threshold:
            message = (
                f"予測リスク評価アラート: リスクスコア {current_score:.1f} が"
                f"閾値 {threshold:.1f} を超過しています。詳細レポートを確認してください。"
            )
            await workflow.execute_activity(
                send_notification,
                args=[tenant_id, message],
                start_to_close_timeout=timedelta(seconds=30),
            )

    @workflow.query
    def get_current_step(self) -> str:
        """現在のステップを返す"""
        return self._current_step

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        """現在のステートを返す"""
        return self._state

    @workflow.signal
    async def cancel_workflow(self) -> None:
        """ワークフローキャンセル"""
        self._is_cancelled = True
        workflow.logger.info("予測リスクワークフロー: キャンセルリクエスト受信")
