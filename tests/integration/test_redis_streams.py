"""Redis Streams 統合テスト — 実際のRedis接続を使用"""

import os
from uuid import uuid4

import pytest

from src.dialogue.protocol import QuestionMessage
from src.dialogue.redis_bus import RedisStreamsBus


def _redis_available() -> bool:
    """Redis接続が利用可能かチェック"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis

        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _redis_available(), reason="Redis未起動")
class TestRedisStreamsIntegration:
    """Redis Streams 統合テスト"""

    @pytest.fixture
    async def redis_bus(self) -> RedisStreamsBus:
        """実Redis接続のバス"""
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=False)
        bus = RedisStreamsBus(redis_client=client)
        yield bus  # type: ignore[misc]
        await bus.close()

    async def test_send_and_retrieve(self, redis_bus: RedisStreamsBus) -> None:
        """送信→取得の往復テスト"""
        auditor_id = uuid4()
        auditee_id = uuid4()

        msg = QuestionMessage(
            from_tenant_id=auditor_id,
            to_tenant_id=auditee_id,
            from_agent="auditor_controls_tester",
            content="統合テスト: Redis Streams送受信確認",
        )

        result = await redis_bus.send(msg)
        assert result.thread_id is not None

        # テナント宛メッセージの取得
        messages = await redis_bus.get_messages_for_tenant(auditee_id)
        assert len(messages) >= 1
        found = any(m.id == msg.id for m in messages)
        assert found, "送信したメッセージがテナントStreamに存在する"

    async def test_thread_retrieval(self, redis_bus: RedisStreamsBus) -> None:
        """スレッド取得テスト"""
        auditor_id = uuid4()
        auditee_id = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor_id,
            to_tenant_id=auditee_id,
            from_agent="auditor_controls_tester",
            content="スレッドテスト質問",
        )
        sent = await redis_bus.send(q)

        thread = await redis_bus.get_thread(sent.thread_id)
        assert len(thread) >= 1

    async def test_consumer_group_read(self, redis_bus: RedisStreamsBus) -> None:
        """Consumer Group読み取りテスト"""
        auditor_id = uuid4()
        auditee_id = uuid4()

        msg = QuestionMessage(
            from_tenant_id=auditor_id,
            to_tenant_id=auditee_id,
            from_agent="test",
            content="コンシューマーグループテスト",
        )
        await redis_bus.send(msg)

        # Consumer Groupとして読み取り
        messages = await redis_bus.read_as_consumer(auditee_id, f"test-consumer-{uuid4()}")

        assert len(messages) >= 1
        entry_id, read_msg = messages[0]
        assert entry_id is not None

        # ACK
        ack_count = await redis_bus.ack(auditee_id, [entry_id])
        assert ack_count >= 1
