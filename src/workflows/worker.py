"""Temporal Worker — Activity/Workflowを実行するワーカープロセス"""

import asyncio

from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from src.config.settings import get_settings
from src.workflows.activities import (
    check_approval_status,
    run_auditee_agent,
    run_auditor_agent,
    send_notification,
)
from src.workflows.audit_workflow import AuditProjectWorkflow
from src.workflows.auditee_workflow import (
    AuditeeResponseWorkflow,
    ControlsMonitoringWorkflow,
)
from src.workflows.self_assessment import SelfAssessmentWorkflow

TASK_QUEUE = "audit-agent-tasks"


async def start_worker() -> None:
    """Temporal Workerを起動"""
    settings = get_settings()

    logger.info(
        "Temporal Worker起動: host={}, namespace={}",
        settings.temporal_host,
        settings.temporal_namespace,
    )

    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            AuditProjectWorkflow,
            AuditeeResponseWorkflow,
            ControlsMonitoringWorkflow,
            SelfAssessmentWorkflow,
        ],
        activities=[
            run_auditor_agent,
            run_auditee_agent,
            send_notification,
            check_approval_status,
        ],
    )

    logger.info("Temporal Worker稼働開始: task_queue={}", TASK_QUEUE)
    await worker.run()


async def start_workflow(
    workflow_type: str,
    workflow_id: str,
    args: dict,  # type: ignore[type-arg]
) -> str:
    """ワークフローを開始するヘルパー"""
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    workflow_map = {
        "audit_project": AuditProjectWorkflow.run,
        "auditee_response": AuditeeResponseWorkflow.run,
        "controls_monitoring": ControlsMonitoringWorkflow.run,
        "self_assessment": SelfAssessmentWorkflow.run,
    }

    workflow_fn = workflow_map.get(workflow_type)
    if not workflow_fn:
        raise ValueError(f"Unknown workflow: {workflow_type}")

    handle = await client.start_workflow(  # type: ignore[var-annotated]
        workflow_fn,  # type: ignore[arg-type]
        **args,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    logger.info("ワークフロー開始: type={}, id={}", workflow_type, handle.id)
    return handle.id


def main() -> None:
    """エントリーポイント"""
    asyncio.run(start_worker())


if __name__ == "__main__":
    main()
