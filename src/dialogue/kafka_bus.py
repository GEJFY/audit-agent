"""Kafka Bus — Dialogue Busのエンタープライズ版メッセージブローカー"""

import json
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from src.config.constants import DialogueMessageType
from src.config.settings import get_settings
from src.dialogue.escalation import EscalationEngine
from src.dialogue.protocol import DialogueMessageSchema, EscalationMessage
from src.dialogue.quality import QualityEvaluator
from src.monitoring.metrics import dialogue_messages_total


class KafkaBus:
    """Kafka (Redpanda) ベースのメッセージバス

    Dialogue Bus のバックエンドとして動作。
    各テナント間のメッセージを永続化・ルーティング。
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._producer: Any = None
        self._consumer: Any = None
        self._topic = self._settings.kafka_topic_dialogue
        self._bootstrap_servers = self._settings.kafka_bootstrap_servers
        self._handlers: dict[str, list[Callable[..., Any]]] = {}

    async def connect(self) -> bool:
        """Kafkaプロデューサー/コンシューマー接続"""
        if not self._bootstrap_servers:
            logger.warning("Kafka: bootstrap_serversが未設定")
            return False

        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()

            logger.info("Kafka Producer接続成功: {}", self._bootstrap_servers)
            return True
        except Exception as e:
            logger.error("Kafka接続エラー: {}", str(e))
            return False

    async def disconnect(self) -> None:
        """接続切断"""
        if self._producer:
            await self._producer.stop()
            self._producer = None
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

    async def publish(
        self,
        message: DialogueMessageSchema,
        topic: str | None = None,
    ) -> bool:
        """メッセージをKafkaトピックに送信"""
        if not self._producer:
            connected = await self.connect()
            if not connected:
                return False

        target_topic = topic or self._topic
        key = str(message.to_tenant_id)

        try:
            payload = {
                "id": str(message.id),
                "timestamp": message.timestamp.isoformat(),
                "from_tenant_id": str(message.from_tenant_id),
                "to_tenant_id": str(message.to_tenant_id),
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type.value,
                "subject": message.subject,
                "content": message.content,
                "project_id": str(message.project_id) if message.project_id else None,
                "thread_id": str(message.thread_id) if message.thread_id else None,
                "confidence": message.confidence,
                "quality_score": message.quality_score,
                "is_escalated": message.is_escalated,
                "metadata": message.metadata,
            }

            await self._producer.send_and_wait(
                target_topic,
                value=payload,
                key=key,
            )

            logger.debug(
                "Kafka送信: topic={}, key={}, msg_id={}",
                target_topic,
                key,
                str(message.id),
            )
            return True
        except Exception as e:
            logger.error("Kafka送信エラー: {}", str(e))
            return False

    async def start_consumer(
        self,
        group_id: str = "audit-agent-dialogue",
        topics: list[str] | None = None,
    ) -> None:
        """Kafkaコンシューマーを開始（バックグラウンド）"""
        if not self._bootstrap_servers:
            logger.warning("Kafka Consumer: bootstrap_serversが未設定")
            return

        try:
            from aiokafka import AIOKafkaConsumer

            target_topics = topics or [self._topic]

            self._consumer = AIOKafkaConsumer(
                *target_topics,
                bootstrap_servers=self._bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            await self._consumer.start()
            logger.info(
                "Kafka Consumer開始: topics={}, group={}",
                target_topics,
                group_id,
            )

            async for msg in self._consumer:
                await self._dispatch_message(msg.value)

        except Exception as e:
            logger.error("Kafka Consumer エラー: {}", str(e))
        finally:
            if self._consumer:
                await self._consumer.stop()

    def on_message(self, tenant_id: str, handler: Callable[..., Any]) -> None:
        """テナント単位のメッセージハンドラ登録"""
        if tenant_id not in self._handlers:
            self._handlers[tenant_id] = []
        self._handlers[tenant_id].append(handler)

    async def _dispatch_message(self, payload: dict[str, Any]) -> None:
        """受信メッセージをハンドラに振り分け"""
        to_tenant = payload.get("to_tenant_id", "")
        handlers = self._handlers.get(to_tenant, [])

        for handler in handlers:
            try:
                await handler(payload)
            except Exception as e:
                logger.error("Kafkaメッセージハンドラエラー: {}", str(e))

        # WebSocket接続があればリアルタイム転送
        try:
            from src.api.routes.websocket import get_connection_manager

            ws_manager = get_connection_manager()
            await ws_manager.broadcast_to_tenant(
                to_tenant,
                {
                    "type": "dialogue_message",
                    "data": payload,
                },
            )
        except Exception:
            logger.debug("WebSocket未起動のためスキップ")


class KafkaDialogueBus:
    """DialogueBusインターフェース互換のKafkaバックエンド

    DialogueBusと同じsend/subscribe/get_thread APIを提供しつつ、
    メッセージ永続化にKafkaを使用する。ローカルキャッシュ付き。
    """

    def __init__(
        self,
        quality_evaluator: QualityEvaluator | None = None,
        escalation_engine: EscalationEngine | None = None,
    ) -> None:
        self._kafka = KafkaBus()
        self._message_log: list[DialogueMessageSchema] = []
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._threads: dict[UUID, list[DialogueMessageSchema]] = defaultdict(list)
        self._quality_evaluator = quality_evaluator or QualityEvaluator()
        self._escalation_engine = escalation_engine or EscalationEngine()

    async def send(self, message: DialogueMessageSchema) -> DialogueMessageSchema:
        """メッセージをKafka経由で送信"""
        self._validate_message(message)

        if message.thread_id is None:
            message.thread_id = message.id
        self._threads[message.thread_id].append(message)
        self._message_log.append(message)

        dialogue_messages_total.labels(
            message_type=message.message_type.value,
            direction="auditor_to_auditee",
        ).inc()

        logger.info(
            "Kafka対話メッセージ送信",
            message_id=str(message.id),
            from_agent=message.from_agent,
            to_agent=message.to_agent,
        )

        # 回答メッセージの品質評価
        if message.message_type == DialogueMessageType.ANSWER:
            result = await self._quality_evaluator.evaluate_detailed(message, self._threads[message.thread_id])
            message.quality_score = result.score
            message.metadata["quality_breakdown"] = result.breakdown.model_dump()
            if result.issues:
                message.metadata["quality_issues"] = result.issues

        # エスカレーション判定
        if self._escalation_engine.should_escalate(message):
            reason = self._escalation_engine.get_reason(message)
            escalation = EscalationMessage(
                from_tenant_id=message.from_tenant_id,
                to_tenant_id=message.to_tenant_id,
                from_agent=message.from_agent,
                content=f"エスカレーション: {reason.value} — 原メッセージ: {message.content[:200]}",
                project_id=message.project_id,
                parent_message_id=message.id,
                thread_id=message.thread_id,
                escalation_reason=reason,
            )
            self._message_log.append(escalation)

        # Kafkaに永続化
        await self._kafka.publish(message)

        # ローカルサブスクライバーに通知
        tenant_id = str(message.to_tenant_id)
        for callback in self._subscribers.get(tenant_id, []):
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"サブスクライバー通知エラー: {e}")

        return message

    def subscribe(self, tenant_id: str, callback: Callable[..., Any]) -> None:
        """テナント単位でメッセージサブスクライブ"""
        self._subscribers[tenant_id].append(callback)
        self._kafka.on_message(tenant_id, callback)

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


# シングルトン
_kafka_bus: KafkaBus | None = None


def get_kafka_bus() -> KafkaBus:
    """KafkaBusシングルトンを取得"""
    global _kafka_bus
    if _kafka_bus is None:
        _kafka_bus = KafkaBus()
    return _kafka_bus
