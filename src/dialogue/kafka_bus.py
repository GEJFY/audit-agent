"""Kafka Bus — Dialogue Busのエンタープライズ版メッセージブローカー"""

import json
from typing import Any, Callable
from uuid import UUID

from loguru import logger

from src.config.settings import get_settings
from src.dialogue.protocol import DialogueMessageSchema


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
            from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(
                    v, ensure_ascii=False, default=str
                ).encode("utf-8"),
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
                target_topic, key, str(message.id),
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
                target_topics, group_id,
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
            await ws_manager.broadcast_to_tenant(to_tenant, {
                "type": "dialogue_message",
                "data": payload,
            })
        except Exception:
            pass  # WebSocketが未起動の場合はスキップ


# シングルトン
_kafka_bus: KafkaBus | None = None


def get_kafka_bus() -> KafkaBus:
    """KafkaBusシングルトンを取得"""
    global _kafka_bus
    if _kafka_bus is None:
        _kafka_bus = KafkaBus()
    return _kafka_bus
