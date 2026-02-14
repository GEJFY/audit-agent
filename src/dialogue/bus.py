"""Dialogue Bus — Auditor ⇔ Auditee間の中央対話基盤"""

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from src.config.constants import DialogueMessageType
from src.dialogue.escalation import EscalationEngine
from src.dialogue.protocol import DialogueMessageSchema, EscalationMessage
from src.dialogue.quality import QualityEvaluator
from src.monitoring.metrics import dialogue_messages_total


class DialogueBus:
    """Agent間対話の中央バス

    Phase 0-1: インメモリ + Redis Streams
    Phase 2+: Kafka対応

    責務:
    - メッセージルーティング
    - 対話ログ（Append-Only）
    - 回答品質評価
    - エスカレーション判定
    - 人間オーバーライドポイント
    """

    def __init__(
        self,
        quality_evaluator: QualityEvaluator | None = None,
        escalation_engine: EscalationEngine | None = None,
    ) -> None:
        self._message_log: list[DialogueMessageSchema] = []  # Append-Only
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._threads: dict[UUID, list[DialogueMessageSchema]] = defaultdict(list)
        self._quality_evaluator = quality_evaluator or QualityEvaluator()
        self._escalation_engine = escalation_engine or EscalationEngine()

    async def send(self, message: DialogueMessageSchema) -> DialogueMessageSchema:
        """メッセージを送信

        1. バリデーション
        2. 対話ログに記録（Append-Only）
        3. 品質評価（回答メッセージの場合）
        4. エスカレーション判定
        5. サブスクライバーに通知
        """
        # バリデーション
        self._validate_message(message)

        # スレッド管理
        if message.thread_id is None:
            message.thread_id = message.id  # 新規スレッド
        self._threads[message.thread_id].append(message)

        # Append-Only ログ
        self._message_log.append(message)

        # メトリクス
        direction = self._determine_direction(message)
        dialogue_messages_total.labels(
            message_type=message.message_type.value,
            direction=direction,
        ).inc()

        logger.info(
            "対話メッセージ送信",
            message_id=str(message.id),
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            message_type=message.message_type.value,
            thread_id=str(message.thread_id),
        )

        # 回答メッセージの品質評価
        if message.message_type == DialogueMessageType.ANSWER:
            quality_score = await self._quality_evaluator.evaluate(message, self._threads[message.thread_id])
            message.quality_score = quality_score

        # エスカレーション判定
        should_escalate = self._escalation_engine.should_escalate(message)
        if should_escalate:
            escalation = await self._create_escalation(message)
            self._message_log.append(escalation)

        # サブスクライバー通知
        await self._notify_subscribers(message)

        return message

    def subscribe(self, tenant_id: str, callback: Callable[..., Any]) -> None:
        """テナント単位でメッセージサブスクライブ"""
        self._subscribers[tenant_id].append(callback)

    def get_thread(self, thread_id: UUID) -> list[DialogueMessageSchema]:
        """スレッド内の全メッセージを取得"""
        return self._threads.get(thread_id, [])

    def get_messages_for_tenant(self, tenant_id: UUID) -> list[DialogueMessageSchema]:
        """テナント宛メッセージを取得"""
        return [m for m in self._message_log if m.to_tenant_id == tenant_id or m.from_tenant_id == tenant_id]

    def get_pending_approvals(self, tenant_id: UUID) -> list[DialogueMessageSchema]:
        """承認待ちメッセージを取得"""
        return [m for m in self._message_log if m.from_tenant_id == tenant_id and m.human_approved is None]

    def approve_message(self, message_id: UUID, approver_id: UUID) -> bool:
        """メッセージを承認"""
        for msg in self._message_log:
            if msg.id == message_id:
                msg.human_approved = True
                msg.approved_by = approver_id
                msg.approved_at = datetime.now(UTC)
                logger.info(f"メッセージ承認: {message_id}")
                return True
        return False

    def _validate_message(self, message: DialogueMessageSchema) -> None:
        """メッセージバリデーション"""
        if message.from_tenant_id == message.to_tenant_id:
            raise ValueError("送信元と送信先が同一テナント")
        if not message.content:
            raise ValueError("メッセージ内容が空")

    def _determine_direction(self, message: DialogueMessageSchema) -> str:
        """対話方向を判定"""
        # 簡易判定（実際にはテナントのタイプで判定）
        return "auditor_to_auditee"

    async def _create_escalation(self, original: DialogueMessageSchema) -> EscalationMessage:
        """エスカレーションメッセージ作成"""
        reason = self._escalation_engine.get_reason(original)
        return EscalationMessage(
            from_tenant_id=original.from_tenant_id,
            to_tenant_id=original.to_tenant_id,
            from_agent=original.from_agent,
            content=f"エスカレーション: {reason.value} — 原メッセージ: {original.content[:200]}",
            project_id=original.project_id,
            parent_message_id=original.id,
            thread_id=original.thread_id,
            escalation_reason=reason,
        )

    async def _notify_subscribers(self, message: DialogueMessageSchema) -> None:
        """サブスクライバーに通知"""
        tenant_id = str(message.to_tenant_id)
        for callback in self._subscribers.get(tenant_id, []):
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"サブスクライバー通知エラー: {e}")

        # Kafka連携（設定されている場合）
        try:
            from src.dialogue.kafka_bus import get_kafka_bus

            kafka_bus = get_kafka_bus()
            await kafka_bus.publish(message)
        except Exception:
            logger.debug("Kafka未起動のためスキップ")

        # WebSocketリアルタイム通知
        try:
            from src.api.routes.websocket import get_connection_manager

            ws_manager = get_connection_manager()
            await ws_manager.broadcast_to_tenant(
                tenant_id,
                {
                    "type": "dialogue_message",
                    "data": {
                        "id": str(message.id),
                        "from_agent": message.from_agent,
                        "message_type": message.message_type.value,
                        "content": message.content[:200],
                        "timestamp": message.timestamp.isoformat(),
                    },
                },
            )
        except Exception:
            logger.debug("WebSocket未起動のためスキップ")
