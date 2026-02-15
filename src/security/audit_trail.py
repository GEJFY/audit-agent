"""監査証跡 — Append-Only操作ログ"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, Field

from src.security.encryption import HashChain


class AuditEntry(BaseModel):
    """監査証跡エントリ"""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: UUID
    user_id: UUID | None = None
    agent_name: str | None = None
    action: str  # create, update, delete, execute, approve, reject
    resource_type: str  # project, finding, evidence, dialogue, agent_decision
    resource_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None  # Agent判断時の信頼度
    hash: str = ""  # ハッシュチェーン値
    previous_hash: str = ""  # 前エントリのハッシュ


class AuditTrailService:
    """監査証跡サービス — 全操作のAppend-Only記録

    改ざん防止のためハッシュチェーンを使用。
    データベース永続化は Repository層で実行。
    """

    def __init__(self) -> None:
        self._hash_chain = HashChain()
        self._buffer: list[AuditEntry] = []

    def record(
        self,
        tenant_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: UUID | None = None,
        agent_name: str | None = None,
        details: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> AuditEntry:
        """操作を記録

        Args:
            tenant_id: テナントID
            action: 操作種別
            resource_type: リソース種別
            resource_id: リソースID
            user_id: 操作ユーザーID（人間の場合）
            agent_name: 操作Agent名（AIの場合）
            details: 追加詳細情報
            confidence: Agent判断の信頼度（0.0-1.0）
        """
        entry = AuditEntry(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_name=agent_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            confidence=confidence,
        )

        # ハッシュチェーンに追加
        entry_data = entry.model_dump(exclude={"hash", "previous_hash"})
        entry.hash = self._hash_chain.add_entry(entry_data)

        self._buffer.append(entry)

        logger.info(
            "監査証跡記録",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            agent_name=agent_name,
            confidence=confidence,
        )

        return entry

    def flush(self) -> list[AuditEntry]:
        """バッファをフラッシュしてエントリ一覧を返す（DB永続化用）"""
        entries = self._buffer.copy()
        self._buffer.clear()
        return entries

    def record_agent_decision(
        self,
        tenant_id: UUID,
        agent_name: str,
        decision: str,
        reasoning: str,
        confidence: float,
        resource_type: str,
        resource_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Agent判断を記録（根拠・信頼度を含む）"""
        return self.record(
            tenant_id=tenant_id,
            agent_name=agent_name,
            action="agent_decision",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "decision": decision,
                "reasoning": reasoning,
                "input_summary": input_data or {},
            },
            confidence=confidence,
        )
