"""エージェント操作エンドポイント — DB + Agent Registry連携"""

import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, get_llm_gateway
from src.api.middleware.auth import require_permission
from src.api.schemas.agents import (
    AgentDecisionListResponse,
    AgentDecisionResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentListResponse,
    ApprovalActionRequest,
    ApprovalQueueItem,
)
from src.db.models.auditor import AgentDecision, ApprovalQueue
from src.llm_gateway.gateway import LLMGateway
from src.security.auth import TokenPayload

router = APIRouter()


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    user: TokenPayload = Depends(require_permission("agent:execute")),
) -> AgentListResponse:
    """登録済みAgent一覧"""
    from src.agents.registry import AgentRegistry

    registry = AgentRegistry.get_instance()
    agents = registry.list_agents()

    return AgentListResponse(agents=agents)


@router.post("/execute", response_model=AgentExecuteResponse, status_code=202)
async def execute_agent(
    request: AgentExecuteRequest,
    user: TokenPayload = Depends(require_permission("agent:execute")),
    session: AsyncSession = Depends(get_db_session),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> AgentExecuteResponse:
    """Agent実行 — Registry経由で該当Agentを取得・実行"""
    from src.agents.registry import AgentRegistry

    registry = AgentRegistry.get_instance()

    # Agent存在確認
    agent = registry.get_agent(request.agent_name)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{request.agent_name}' が登録されていません",
        )

    # 実行IDを生成（追跡用）
    execution_id = str(uuid_mod.uuid4())

    # Agent判断レコードを先に作成（実行中ステータス）
    decision = AgentDecision(
        tenant_id=user.tenant_id,
        project_id=request.project_id,
        agent_type=request.agent_name,
        decision_type="execution",
        input_summary={"parameters": request.parameters or {}, "execution_id": execution_id},
        confidence=0.0,
        model_used="pending",
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)

    # Agent実行（初期ステートを構成）
    initial_state: dict[str, Any] = {
        "messages": [],
        "project_id": request.project_id or "",
        "tenant_id": user.tenant_id,
        **(request.parameters or {}),
    }

    try:
        result_state = await agent.run(initial_state)

        # 結果をDB更新
        decision.output_summary = {
            "status": "completed",
            "result_keys": list(result_state.keys()) if isinstance(result_state, dict) else [],
        }
        decision.confidence = result_state.get("confidence", 0.8) if isinstance(result_state, dict) else 0.8
        decision.model_used = "claude-sonnet-4-5"
        await session.commit()

        return AgentExecuteResponse(
            agent_name=request.agent_name,
            status="completed",
            message=f"Agent '{request.agent_name}' の実行が完了しました",
            execution_id=execution_id,
            result=result_state if isinstance(result_state, dict) else {"output": str(result_state)},
        )
    except Exception as e:
        decision.output_summary = {"status": "failed", "error": str(e)}
        decision.confidence = 0.0
        decision.model_used = "error"
        await session.commit()

        return AgentExecuteResponse(
            agent_name=request.agent_name,
            status="failed",
            message=f"Agent実行エラー: {e!s}",
            execution_id=execution_id,
        )


@router.get("/decisions", response_model=AgentDecisionListResponse)
async def list_agent_decisions(
    user: TokenPayload = Depends(require_permission("agent:approve")),
    session: AsyncSession = Depends(get_db_session),
    decision_status: str | None = None,
    agent_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> AgentDecisionListResponse:
    """Agent判断履歴"""
    query = select(AgentDecision).where(AgentDecision.tenant_id == user.tenant_id)

    if agent_type:
        query = query.where(AgentDecision.agent_type == agent_type)
    if decision_status == "pending_approval":
        query = query.where(AgentDecision.human_approved.is_(None))
    elif decision_status == "approved":
        query = query.where(AgentDecision.human_approved.is_(True))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    query = query.order_by(AgentDecision.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    decisions = result.scalars().all()

    return AgentDecisionListResponse(
        decisions=[
            AgentDecisionResponse(
                id=d.id,
                agent_type=d.agent_type,
                decision_type=d.decision_type,
                reasoning=d.reasoning,
                confidence=d.confidence,
                model_used=d.model_used,
                human_approved=d.human_approved,
                project_id=d.project_id,
                created_at=d.created_at if hasattr(d, "created_at") else None,
            )
            for d in decisions
        ],
        total=total,
    )


@router.post("/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: str,
    body: ApprovalActionRequest,
    user: TokenPayload = Depends(require_permission("agent:approve")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Agent判断を承認 / 却下"""
    result = await session.execute(
        select(AgentDecision).where(
            AgentDecision.id == decision_id,
            AgentDecision.tenant_id == user.tenant_id,
        )
    )
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="判断レコードが見つかりません")

    decision.human_approved = body.action == "approved"
    decision.approved_by = user.sub
    await session.commit()

    # 承認キューにも反映
    queue_result = await session.execute(select(ApprovalQueue).where(ApprovalQueue.decision_id == decision_id))
    queue_item = queue_result.scalar_one_or_none()
    if queue_item:
        queue_item.status = body.action
        queue_item.resolved_at = datetime.now(UTC).isoformat()
        queue_item.resolution_comment = body.comment
        await session.commit()

    return {"status": body.action, "decision_id": decision_id}


@router.get("/approval-queue", response_model=list[ApprovalQueueItem])
async def list_approval_queue(
    user: TokenPayload = Depends(require_permission("agent:approve")),
    session: AsyncSession = Depends(get_db_session),
    priority: str | None = None,
) -> list[ApprovalQueueItem]:
    """承認キュー一覧"""
    query = select(ApprovalQueue).where(
        ApprovalQueue.tenant_id == user.tenant_id,
        ApprovalQueue.status == "pending",
    )
    if priority:
        query = query.where(ApprovalQueue.priority == priority)

    query = query.order_by(
        ApprovalQueue.priority.desc(),
        ApprovalQueue.created_at.asc(),
    )

    result = await session.execute(query)
    items = result.scalars().all()

    return [
        ApprovalQueueItem(
            id=item.id,
            decision_id=item.decision_id,
            approval_type=item.approval_type,
            priority=item.priority,
            status=item.status,
            requested_by_agent=item.requested_by_agent,
            context=item.context,
            created_at=item.created_at if hasattr(item, "created_at") else None,
        )
        for item in items
    ]
