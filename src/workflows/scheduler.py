"""ワークフロースケジューラ — Temporal Cron Schedule管理"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from loguru import logger


@dataclass
class ScheduleConfig:
    """スケジュール設定"""

    schedule_id: str
    workflow_name: str
    cron_expression: str
    tenant_id: str
    args: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    task_queue: str = "audit-agent-queue"
    execution_timeout: timedelta = field(default_factory=lambda: timedelta(minutes=30))


class WorkflowScheduler:
    """Temporal Cron Scheduleを管理するスケジューラ

    統制モニタリングの日次実行、セルフアセスメントの四半期実行など、
    定期的なワークフロー実行をテナント単位で管理する。
    """

    # デフォルトスケジュールテンプレート
    DEFAULT_SCHEDULES = {
        "controls_monitoring_daily": {
            "workflow_name": "ControlsMonitoringWorkflow",
            "cron_expression": "0 2 * * *",  # 毎日AM2:00
            "description": "統制モニタリング日次実行",
        },
        "risk_alert_check": {
            "workflow_name": "ControlsMonitoringWorkflow",
            "cron_expression": "0 */6 * * *",  # 6時間ごと
            "description": "リスクアラートチェック",
        },
        "self_assessment_quarterly": {
            "workflow_name": "SelfAssessmentWorkflow",
            "cron_expression": "0 9 1 1,4,7,10 *",  # 四半期初日AM9:00
            "description": "セルフアセスメント四半期実行",
        },
    }

    def __init__(self) -> None:
        self._schedules: dict[str, ScheduleConfig] = {}
        self._client: Any = None

    async def connect(self, temporal_host: str, namespace: str = "audit-agent") -> bool:
        """Temporalクライアントに接続"""
        try:
            from temporalio.client import Client

            self._client = await Client.connect(temporal_host, namespace=namespace)
            logger.info("Temporal Scheduler接続成功: {}", temporal_host)
            return True
        except Exception as e:
            logger.error("Temporal Scheduler接続エラー: {}", str(e))
            return False

    def register_schedule(self, config: ScheduleConfig) -> None:
        """スケジュールを登録"""
        self._schedules[config.schedule_id] = config
        logger.info(
            "スケジュール登録: id={}, workflow={}, cron={}",
            config.schedule_id,
            config.workflow_name,
            config.cron_expression,
        )

    def unregister_schedule(self, schedule_id: str) -> bool:
        """スケジュールを解除"""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            logger.info("スケジュール解除: {}", schedule_id)
            return True
        return False

    def get_schedule(self, schedule_id: str) -> ScheduleConfig | None:
        """スケジュール設定を取得"""
        return self._schedules.get(schedule_id)

    def list_schedules(self, tenant_id: str | None = None) -> list[ScheduleConfig]:
        """スケジュール一覧を取得"""
        schedules = list(self._schedules.values())
        if tenant_id:
            schedules = [s for s in schedules if s.tenant_id == tenant_id]
        return schedules

    def register_tenant_defaults(self, tenant_id: str) -> list[str]:
        """テナントにデフォルトスケジュールを一括登録

        Returns:
            登録されたスケジュールIDのリスト
        """
        registered_ids: list[str] = []
        for template_key, template in self.DEFAULT_SCHEDULES.items():
            schedule_id = f"{tenant_id}_{template_key}"
            config = ScheduleConfig(
                schedule_id=schedule_id,
                workflow_name=template["workflow_name"],
                cron_expression=template["cron_expression"],
                tenant_id=tenant_id,
            )
            self.register_schedule(config)
            registered_ids.append(schedule_id)

        logger.info(
            "テナントデフォルトスケジュール登録完了: tenant={}, count={}",
            tenant_id,
            len(registered_ids),
        )
        return registered_ids

    async def start_schedule(self, schedule_id: str) -> bool:
        """スケジュールを開始（Temporal Schedule API）"""
        config = self._schedules.get(schedule_id)
        if not config:
            logger.warning("スケジュール未登録: {}", schedule_id)
            return False

        if not config.enabled:
            logger.info("スケジュール無効: {}", schedule_id)
            return False

        if not self._client:
            logger.warning("Temporal未接続")
            return False

        try:
            from temporalio.client import (
                Schedule,
                ScheduleActionStartWorkflow,
                ScheduleSpec,
            )

            await self._client.create_schedule(
                schedule_id,
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        config.workflow_name,
                        arg=config.tenant_id,
                        id=f"{config.workflow_name}-{config.tenant_id}",
                        task_queue=config.task_queue,
                        execution_timeout=config.execution_timeout,
                    ),
                    spec=ScheduleSpec(
                        cron_expressions=[config.cron_expression],
                    ),
                ),
            )

            logger.info("スケジュール開始: {}", schedule_id)
            return True
        except Exception as e:
            logger.error("スケジュール開始エラー: {} — {}", schedule_id, str(e))
            return False

    async def stop_schedule(self, schedule_id: str) -> bool:
        """スケジュールを停止"""
        if not self._client:
            return False

        try:
            handle = self._client.get_schedule_handle(schedule_id)
            await handle.delete()
            logger.info("スケジュール停止: {}", schedule_id)
            return True
        except Exception as e:
            logger.error("スケジュール停止エラー: {} — {}", schedule_id, str(e))
            return False

    def enable_schedule(self, schedule_id: str) -> bool:
        """スケジュールを有効化"""
        config = self._schedules.get(schedule_id)
        if config:
            config.enabled = True
            return True
        return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """スケジュールを無効化"""
        config = self._schedules.get(schedule_id)
        if config:
            config.enabled = False
            return True
        return False
