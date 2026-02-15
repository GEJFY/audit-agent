"""ワークフロースケジューラ テスト"""

from datetime import timedelta

import pytest

from src.workflows.scheduler import ScheduleConfig, WorkflowScheduler


@pytest.mark.unit
class TestWorkflowScheduler:
    """WorkflowScheduler テスト"""

    def test_register_schedule(self) -> None:
        """スケジュール登録"""
        scheduler = WorkflowScheduler()
        config = ScheduleConfig(
            schedule_id="tenant1_daily",
            workflow_name="ControlsMonitoringWorkflow",
            cron_expression="0 2 * * *",
            tenant_id="tenant1",
        )

        scheduler.register_schedule(config)

        assert scheduler.get_schedule("tenant1_daily") is not None
        assert scheduler.get_schedule("tenant1_daily").workflow_name == "ControlsMonitoringWorkflow"

    def test_unregister_schedule(self) -> None:
        """スケジュール解除"""
        scheduler = WorkflowScheduler()
        config = ScheduleConfig(
            schedule_id="test_schedule",
            workflow_name="TestWorkflow",
            cron_expression="0 * * * *",
            tenant_id="tenant1",
        )
        scheduler.register_schedule(config)

        result = scheduler.unregister_schedule("test_schedule")
        assert result is True
        assert scheduler.get_schedule("test_schedule") is None

    def test_unregister_nonexistent(self) -> None:
        """存在しないスケジュールの解除"""
        scheduler = WorkflowScheduler()
        result = scheduler.unregister_schedule("nonexistent")
        assert result is False

    def test_list_schedules(self) -> None:
        """スケジュール一覧"""
        scheduler = WorkflowScheduler()

        for i in range(3):
            scheduler.register_schedule(
                ScheduleConfig(
                    schedule_id=f"schedule_{i}",
                    workflow_name="TestWorkflow",
                    cron_expression="0 * * * *",
                    tenant_id=f"tenant_{i % 2}",
                )
            )

        all_schedules = scheduler.list_schedules()
        assert len(all_schedules) == 3

        tenant0_schedules = scheduler.list_schedules(tenant_id="tenant_0")
        assert len(tenant0_schedules) == 2

        tenant1_schedules = scheduler.list_schedules(tenant_id="tenant_1")
        assert len(tenant1_schedules) == 1

    def test_register_tenant_defaults(self) -> None:
        """テナントデフォルトスケジュール一括登録"""
        scheduler = WorkflowScheduler()

        ids = scheduler.register_tenant_defaults("tenant_abc")

        assert len(ids) == len(WorkflowScheduler.DEFAULT_SCHEDULES)
        for schedule_id in ids:
            assert schedule_id.startswith("tenant_abc_")
            config = scheduler.get_schedule(schedule_id)
            assert config is not None
            assert config.tenant_id == "tenant_abc"

    def test_enable_disable_schedule(self) -> None:
        """スケジュール有効/無効切替"""
        scheduler = WorkflowScheduler()
        config = ScheduleConfig(
            schedule_id="test",
            workflow_name="TestWorkflow",
            cron_expression="0 * * * *",
            tenant_id="tenant1",
            enabled=True,
        )
        scheduler.register_schedule(config)

        result = scheduler.disable_schedule("test")
        assert result is True
        assert scheduler.get_schedule("test").enabled is False

        result = scheduler.enable_schedule("test")
        assert result is True
        assert scheduler.get_schedule("test").enabled is True

    def test_enable_nonexistent(self) -> None:
        """存在しないスケジュールの有効化"""
        scheduler = WorkflowScheduler()
        assert scheduler.enable_schedule("nonexistent") is False
        assert scheduler.disable_schedule("nonexistent") is False

    def test_schedule_config_defaults(self) -> None:
        """ScheduleConfig デフォルト値"""
        config = ScheduleConfig(
            schedule_id="test",
            workflow_name="TestWorkflow",
            cron_expression="0 * * * *",
            tenant_id="tenant1",
        )

        assert config.enabled is True
        assert config.task_queue == "audit-agent-queue"
        assert config.execution_timeout == timedelta(minutes=30)
        assert config.args == {}

    def test_default_schedules_structure(self) -> None:
        """デフォルトスケジュールの構造確認"""
        for _key, template in WorkflowScheduler.DEFAULT_SCHEDULES.items():
            assert "workflow_name" in template
            assert "cron_expression" in template
            assert "description" in template

    async def test_start_schedule_not_connected(self) -> None:
        """Temporal未接続でのスケジュール開始"""
        scheduler = WorkflowScheduler()
        config = ScheduleConfig(
            schedule_id="test",
            workflow_name="TestWorkflow",
            cron_expression="0 * * * *",
            tenant_id="tenant1",
        )
        scheduler.register_schedule(config)

        result = await scheduler.start_schedule("test")
        assert result is False

    async def test_start_schedule_not_registered(self) -> None:
        """未登録スケジュールの開始"""
        scheduler = WorkflowScheduler()
        result = await scheduler.start_schedule("nonexistent")
        assert result is False

    async def test_start_schedule_disabled(self) -> None:
        """無効スケジュールの開始"""
        scheduler = WorkflowScheduler()
        config = ScheduleConfig(
            schedule_id="test",
            workflow_name="TestWorkflow",
            cron_expression="0 * * * *",
            tenant_id="tenant1",
            enabled=False,
        )
        scheduler.register_schedule(config)

        result = await scheduler.start_schedule("test")
        assert result is False

    async def test_stop_schedule_not_connected(self) -> None:
        """Temporal未接続でのスケジュール停止"""
        scheduler = WorkflowScheduler()
        result = await scheduler.stop_schedule("test")
        assert result is False
