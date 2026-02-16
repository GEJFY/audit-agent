"""Redis Streams ベースの Dialogue Bus — 永続化+非同期メッセージング"""

from __future__ import annotations

import contextlib
import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any
from uuid import UUID

from loguru import logger

from src.config.constants import DialogueMessageType
from src.config.settings import get_settings
from src.dialogue.escalation import EscalationEngine
from src.dialogue.protocol import DialogueMessageSchema, EscalationMessage
from src.dialogue.quality import QualityEvaluator
from src.monitoring.metrics import dialogue_messages_total


def _serialize_message(message: DialogueMessageSchema) -> dict[str, str]:
    """DialogueMessageSchemaをRedis Stream用のフラットなdict[str, str]に変換"""
    data = message.model_dump(mode="json")
    return {"payload": json.dumps(data, ensure_ascii=False, default=str)}


def _deserialize_message(data: dict[bytes, bytes]) -> DialogueMessageSchema:
    """Redis Streamエントリからメッセージを復元"""
    payload = data[b"payload"]
    parsed = json.loads(payload)
    return DialogueMessageSchema.model_validate(parsed)


class RedisStreamsBus:
    """Redis Streams ベースの対話バス

    インメモリDialogueBusと同一インターフェースを提供しつつ、
    Redis Streamsによるメッセージ永続化とConsumer Group対応を実現。

    Stream キー: dialogue:{tenant_id}
    Consumer Group: cg:{tenant_id}
    """

    def __init__(
        self,
        quality_evaluator: QualityEvaluator | None = None,
        escalation_engine: EscalationEngine | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self._quality_evaluator = quality_evaluator or QualityEvaluator()
        self._escalation_engine = escalation_engine or EscalationEngine()
        self._redis = redis_client
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._local_threads: dict[UUID, list[DialogueMessageSchema]] = defaultdict(list)

    async def _get_redis(self) -> Any:
        """Redis接続を遅延取得"""
        if self._redis is None:
            import redis.asyncio as aioredis

            settings = get_settings()
            self._redis = aioredis.from_url(  # type: ignore[no-untyped-call]
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=False,
            )
        return self._redis

    async def _ensure_consumer_group(self, stream_key: str, group_name: str) -> None:
        """Consumer Groupが存在しない場合は作成"""
        r = await self._get_redis()
        with contextlib.suppress(Exception):
            await r.xgroup_create(stream_key, group_name, id="0", mkstream=True)

    def _stream_key(self, tenant_id: UUID | str) -> str:
        """テナント単位のStreamキーを生成"""
        return f"dialogue:{tenant_id}"

    def _thread_key(self, thread_id: UUID | str) -> str:
        """スレッド単位のStreamキーを生成"""
        return f"dialogue:thread:{thread_id}"

    def _group_name(self, tenant_id: UUID | str) -> str:
        """Consumer Group名を生成"""
        return f"cg:{tenant_id}"

    async def send(self, message: DialogueMessageSchema) -> DialogueMessageSchema:
        """メッセージを送信

        1. バリデーション
        2. スレッド管理
        3. Redis Streamに永続化
        4. 品質評価（回答メッセージの場合）
        5. エスカレーション判定
        6. サブスクライバーに通知
        """
        self._validate_message(message)

        # スレッド管理
        if message.thread_id is None:
            message.thread_id = message.id
        self._local_threads[message.thread_id].append(message)

        # Redis Streamsに永続化
        r = await self._get_redis()
        serialized = _serialize_message(message)

        # 送信先テナントのStreamに追加
        to_stream = self._stream_key(message.to_tenant_id)
        await self._ensure_consumer_group(to_stream, self._group_name(message.to_tenant_id))
        await r.xadd(to_stream, serialized)

        # 送信元テナントのStreamにも記録（Append-Onlyログ）
        from_stream = self._stream_key(message.from_tenant_id)
        await self._ensure_consumer_group(from_stream, self._group_name(message.from_tenant_id))
        await r.xadd(from_stream, serialized)

        # スレッドStreamにも記録
        thread_stream = self._thread_key(message.thread_id)
        await r.xadd(thread_stream, serialized)

        # メトリクス
        direction = self._determine_direction(message)
        dialogue_messages_total.labels(
            message_type=message.message_type.value,
            direction=direction,
        ).inc()

        logger.info(
            "対話メッセージ送信（Redis Streams）",
            message_id=str(message.id),
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            message_type=message.message_type.value,
            thread_id=str(message.thread_id),
        )

        # 回答メッセージの品質評価
        if message.message_type == DialogueMessageType.ANSWER:
            quality_score = await self._quality_evaluator.evaluate(message, self._local_threads[message.thread_id])
            message.quality_score = quality_score

        # エスカレーション判定
        should_escalate = self._escalation_engine.should_escalate(message)
        if should_escalate:
            escalation = await self._create_escalation(message)
            escalation_serialized = _serialize_message(escalation)
            await r.xadd(to_stream, escalation_serialized)

        # サブスクライバー通知
        await self._notify_subscribers(message)

        return message

    def subscribe(self, tenant_id: str, callback: Callable[..., Any]) -> None:
        """テナント単位でメッセージサブスクライブ"""
        self._subscribers[tenant_id].append(callback)

    async def get_thread(self, thread_id: UUID) -> list[DialogueMessageSchema]:
        """スレッド内の全メッセージをRedis Streamsから取得"""
        r = await self._get_redis()
        thread_stream = self._thread_key(thread_id)

        try:
            entries = await r.xrange(thread_stream)
        except Exception:
            # Streamが存在しない場合はローカルキャッシュにフォールバック
            return self._local_threads.get(thread_id, [])

        messages = []
        for _entry_id, data in entries:
            try:
                msg = _deserialize_message(data)
                messages.append(msg)
            except Exception as e:
                logger.warning(f"メッセージデシリアライズエラー: {e}")

        return messages or self._local_threads.get(thread_id, [])

    async def get_messages_for_tenant(
        self,
        tenant_id: UUID,
        count: int = 100,
    ) -> list[DialogueMessageSchema]:
        """テナント宛メッセージをRedis Streamsから取得"""
        r = await self._get_redis()
        stream_key = self._stream_key(tenant_id)

        try:
            entries = await r.xrevrange(stream_key, count=count)
        except Exception:
            return []

        messages = []
        for _entry_id, data in entries:
            try:
                msg = _deserialize_message(data)
                messages.append(msg)
            except Exception as e:
                logger.warning(f"メッセージデシリアライズエラー: {e}")

        return messages

    async def read_as_consumer(
        self,
        tenant_id: UUID,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 0,
    ) -> list[tuple[str, DialogueMessageSchema]]:
        """Consumer Groupとしてメッセージを読み取り

        Returns: (stream_entry_id, message) のリスト
        """
        r = await self._get_redis()
        stream_key = self._stream_key(tenant_id)
        group_name = self._group_name(tenant_id)

        await self._ensure_consumer_group(stream_key, group_name)

        try:
            results = await r.xreadgroup(
                group_name,
                consumer_name,
                {stream_key: ">"},
                count=count,
                block=block_ms if block_ms > 0 else None,
            )
        except Exception as e:
            logger.warning(f"Consumer読み取りエラー: {e}")
            return []

        messages: list[tuple[str, DialogueMessageSchema]] = []
        for _stream, entries in results:
            for entry_id, data in entries:
                try:
                    msg = _deserialize_message(data)
                    eid = entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)
                    messages.append((eid, msg))
                except Exception as e:
                    logger.warning(f"メッセージデシリアライズエラー: {e}")

        return messages

    async def ack(self, tenant_id: UUID, entry_ids: list[str]) -> int:
        """メッセージの処理完了を確認（ACK）"""
        r = await self._get_redis()
        stream_key = self._stream_key(tenant_id)
        group_name = self._group_name(tenant_id)

        return await r.xack(stream_key, group_name, *entry_ids)  # type: ignore[no-any-return]

    async def get_pending(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """未ACKメッセージ一覧を取得"""
        r = await self._get_redis()
        stream_key = self._stream_key(tenant_id)
        group_name = self._group_name(tenant_id)

        try:
            pending = await r.xpending_range(stream_key, group_name, "-", "+", count=100)
            return [
                {
                    "entry_id": p["message_id"].decode() if isinstance(p["message_id"], bytes) else p["message_id"],
                    "consumer": p["consumer"].decode() if isinstance(p["consumer"], bytes) else p["consumer"],
                    "idle_ms": p["time_since_delivered"],
                    "delivery_count": p["times_delivered"],
                }
                for p in pending
            ]
        except Exception:
            return []

    def _validate_message(self, message: DialogueMessageSchema) -> None:
        """メッセージバリデーション"""
        if message.from_tenant_id == message.to_tenant_id:
            raise ValueError("送信元と送信先が同一テナント")
        if not message.content:
            raise ValueError("メッセージ内容が空")

    def _determine_direction(self, message: DialogueMessageSchema) -> str:
        """対話方向を判定"""
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

    async def close(self) -> None:
        """Redis接続をクローズ"""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
