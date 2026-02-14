"""対話エンドポイント — DB + Dialogue Bus連携"""

import uuid as uuid_mod
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.middleware.auth import require_permission
from src.api.schemas.dialogue import (
    DialogueApproveRequest,
    DialogueListResponse,
    DialogueMessageDetail,
    DialogueMessageResponse,
    DialogueSendRequest,
    ThreadResponse,
)
from src.db.models.dialogue import DialogueMessage
from src.security.auth import TokenPayload

router = APIRouter()


def _msg_to_detail(m: DialogueMessage) -> DialogueMessageDetail:
    return DialogueMessageDetail(
        id=m.id,
        from_tenant_id=m.from_tenant_id,
        to_tenant_id=m.to_tenant_id,
        from_agent=m.from_agent,
        to_agent=m.to_agent,
        message_type=m.message_type,
        subject=m.subject,
        content=m.content,
        project_id=m.project_id,
        thread_id=m.thread_id,
        confidence=m.confidence,
        quality_score=m.quality_score,
        human_approved=m.human_approved,
        is_escalated=m.is_escalated,
        escalation_reason=m.escalation_reason,
        attachments=m.attachments,
        created_at=m.created_at if hasattr(m, "created_at") else None,
    )


@router.get("/messages", response_model=DialogueListResponse)
async def list_messages(
    user: TokenPayload = Depends(require_permission("dialogue:read")),
    session: AsyncSession = Depends(get_db_session),
    project_id: str | None = None,
    thread_id: str | None = None,
    message_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> DialogueListResponse:
    """対話メッセージ一覧 — テナントに関連するメッセージのみ"""
    query = select(DialogueMessage).where(
        or_(
            DialogueMessage.from_tenant_id == user.tenant_id,
            DialogueMessage.to_tenant_id == user.tenant_id,
        )
    )

    if project_id:
        query = query.where(DialogueMessage.project_id == project_id)
    if thread_id:
        query = query.where(DialogueMessage.thread_id == thread_id)
    if message_type:
        query = query.where(DialogueMessage.message_type == message_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    query = query.order_by(DialogueMessage.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    messages = result.scalars().all()

    return DialogueListResponse(
        messages=[_msg_to_detail(m) for m in messages],
        total=total,
    )


@router.post("/send", response_model=DialogueMessageResponse, status_code=201)
async def send_message(
    request: DialogueSendRequest,
    user: TokenPayload = Depends(require_permission("dialogue:send")),
    session: AsyncSession = Depends(get_db_session),
) -> DialogueMessageResponse:
    """対話メッセージ送信 — Dialogue Bus経由でDB記録"""
    # スレッドID決定（新規 or 既存）
    thread_id = None
    if request.parent_message_id:
        parent = await session.execute(select(DialogueMessage).where(DialogueMessage.id == request.parent_message_id))
        parent_msg = parent.scalar_one_or_none()
        if parent_msg:
            thread_id = parent_msg.thread_id or parent_msg.id
    if thread_id is None:
        thread_id = str(uuid_mod.uuid4())

    message = DialogueMessage(
        from_tenant_id=user.tenant_id,
        to_tenant_id=request.to_tenant_id,
        from_agent="api_user",
        to_agent=request.to_agent,
        message_type=request.message_type,
        subject=request.subject,
        content=request.content,
        project_id=request.project_id,
        parent_message_id=request.parent_message_id,
        thread_id=thread_id,
        attachments=request.attachments or [],
        human_approved=None,
        is_escalated=False,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return DialogueMessageResponse(
        id=message.id,
        status="sent",
        message="メッセージを送信しました",
    )


@router.get("/pending", response_model=DialogueListResponse)
async def get_pending_approvals(
    user: TokenPayload = Depends(require_permission("dialogue:approve")),
    session: AsyncSession = Depends(get_db_session),
) -> DialogueListResponse:
    """承認待ちメッセージ一覧"""
    query = (
        select(DialogueMessage)
        .where(
            or_(
                DialogueMessage.from_tenant_id == user.tenant_id,
                DialogueMessage.to_tenant_id == user.tenant_id,
            ),
            DialogueMessage.human_approved.is_(None),
            DialogueMessage.confidence.isnot(None),
        )
        .order_by(DialogueMessage.created_at.asc())
    )

    result = await session.execute(query)
    messages = result.scalars().all()

    return DialogueListResponse(
        messages=[_msg_to_detail(m) for m in messages],
        total=len(messages),
    )


@router.post("/messages/{message_id}/approve")
async def approve_message(
    message_id: str,
    body: DialogueApproveRequest,
    user: TokenPayload = Depends(require_permission("dialogue:approve")),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """メッセージ承認 / 却下"""
    result = await session.execute(select(DialogueMessage).where(DialogueMessage.id == message_id))
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="メッセージが見つかりません")

    # テナント権限チェック
    if message.from_tenant_id != user.tenant_id and message.to_tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="このメッセージを承認する権限がありません")

    message.human_approved = body.approved
    message.approved_by = user.sub
    message.approved_at = datetime.now(UTC).isoformat()

    await session.commit()

    action = "approved" if body.approved else "rejected"
    return {"status": action, "message_id": message_id}


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user: TokenPayload = Depends(require_permission("dialogue:read")),
    session: AsyncSession = Depends(get_db_session),
) -> ThreadResponse:
    """スレッド詳細 — 時系列順のメッセージ一覧"""
    result = await session.execute(
        select(DialogueMessage)
        .where(
            DialogueMessage.thread_id == thread_id,
            or_(
                DialogueMessage.from_tenant_id == user.tenant_id,
                DialogueMessage.to_tenant_id == user.tenant_id,
            ),
        )
        .order_by(DialogueMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return ThreadResponse(
        thread_id=thread_id,
        messages=[_msg_to_detail(m) for m in messages],
        total=len(messages),
    )
