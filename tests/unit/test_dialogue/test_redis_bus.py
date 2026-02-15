"""Redis Streams Dialogue Bus テスト"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dialogue.protocol import AnswerMessage, QuestionMessage
from src.dialogue.redis_bus import RedisStreamsBus, _deserialize_message, _serialize_message


@pytest.fixture
def mock_redis() -> AsyncMock:
    """モックRedisクライアント"""
    r = AsyncMock()
    r.xadd = AsyncMock(return_value=b"1-0")
    r.xrange = AsyncMock(return_value=[])
    r.xrevrange = AsyncMock(return_value=[])
    r.xreadgroup = AsyncMock(return_value=[])
    r.xack = AsyncMock(return_value=1)
    r.xgroup_create = AsyncMock()
    r.xpending_range = AsyncMock(return_value=[])
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def redis_bus(mock_redis: AsyncMock) -> RedisStreamsBus:
    """Redis Streams Bus（モックRedis使用）"""
    return RedisStreamsBus(redis_client=mock_redis)


@pytest.mark.unit
class TestSerialization:
    """メッセージシリアライゼーションテスト"""

    def test_serialize_deserialize_roundtrip(self) -> None:
        """シリアライズ→デシリアライズの往復テスト"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_controls_tester",
            content="テスト質問です",
        )
        serialized = _serialize_message(msg)

        assert "payload" in serialized
        assert isinstance(serialized["payload"], str)

        # バイトに変換（Redis返却値をシミュレート）
        data = {k.encode(): v.encode() for k, v in serialized.items()}
        deserialized = _deserialize_message(data)

        assert deserialized.from_agent == msg.from_agent
        assert deserialized.content == msg.content
        assert deserialized.message_type == msg.message_type

    def test_serialize_with_attachments(self) -> None:
        """添付ファイル付きメッセージのシリアライズ"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="添付テスト",
            attachments=[],
        )
        serialized = _serialize_message(msg)
        assert "payload" in serialized


@pytest.mark.unit
class TestRedisStreamsBus:
    """Redis Streams Bus ユニットテスト"""

    async def test_send_message(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """メッセージ送信テスト — Redis Streamsに永続化"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_controls_tester",
            content="テスト質問",
        )

        result = await redis_bus.send(msg)

        assert result.id == msg.id
        assert result.thread_id is not None
        # xadd が3回呼ばれる（to_stream, from_stream, thread_stream）
        assert mock_redis.xadd.call_count == 3

    async def test_send_creates_consumer_group(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """送信時にConsumer Groupが作成される"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="グループテスト",
        )

        await redis_bus.send(msg)

        # to_stream と from_stream の2つにグループ作成
        assert mock_redis.xgroup_create.call_count == 2

    async def test_thread_management(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """スレッド管理テスト — 同一スレッドにメッセージ追加"""
        auditor_id = uuid4()
        auditee_id = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor_id,
            to_tenant_id=auditee_id,
            from_agent="auditor_controls_tester",
            content="質問です",
        )
        sent_q = await redis_bus.send(q)

        a = AnswerMessage(
            from_tenant_id=auditee_id,
            to_tenant_id=auditor_id,
            from_agent="auditee_response",
            content="回答です。詳細な説明を含む十分な長さの回答文を記載します。" * 5,
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        await redis_bus.send(a)

        # xaddが6回（各メッセージで3回×2）
        assert mock_redis.xadd.call_count == 6

    async def test_validation_same_tenant(self, redis_bus: RedisStreamsBus) -> None:
        """同一テナント送信の検証"""
        tenant_id = uuid4()
        msg = QuestionMessage(
            from_tenant_id=tenant_id,
            to_tenant_id=tenant_id,
            from_agent="test",
            content="test",
        )

        with pytest.raises(ValueError, match="同一テナント"):
            await redis_bus.send(msg)

    async def test_validation_empty_content(self, redis_bus: RedisStreamsBus) -> None:
        """空メッセージの検証"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="",
        )

        with pytest.raises(ValueError, match="空"):
            await redis_bus.send(msg)

    async def test_get_thread_from_redis(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """スレッド取得テスト — Redis Streamsから読み取り"""
        thread_id = uuid4()
        sample_msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="スレッドテスト",
            thread_id=thread_id,
        )
        serialized = _serialize_message(sample_msg)
        entry_data = {k.encode(): v.encode() for k, v in serialized.items()}
        mock_redis.xrange.return_value = [(b"1-0", entry_data)]

        messages = await redis_bus.get_thread(thread_id)

        assert len(messages) == 1
        assert messages[0].content == "スレッドテスト"

    async def test_get_thread_fallback_to_local(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """Redis障害時のローカルキャッシュフォールバック"""
        mock_redis.xrange.side_effect = Exception("Redis接続エラー")

        thread_id = uuid4()
        messages = await redis_bus.get_thread(thread_id)

        # ローカルキャッシュにもなければ空リスト
        assert messages == []

    async def test_get_messages_for_tenant(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """テナント宛メッセージ取得テスト"""
        tenant_id = uuid4()
        sample_msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=tenant_id,
            from_agent="test",
            content="テナントテスト",
        )
        serialized = _serialize_message(sample_msg)
        entry_data = {k.encode(): v.encode() for k, v in serialized.items()}
        mock_redis.xrevrange.return_value = [(b"1-0", entry_data)]

        messages = await redis_bus.get_messages_for_tenant(tenant_id)

        assert len(messages) == 1

    async def test_read_as_consumer(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """Consumer Group読み取りテスト"""
        tenant_id = uuid4()
        sample_msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=tenant_id,
            from_agent="test",
            content="コンシューマーテスト",
        )
        serialized = _serialize_message(sample_msg)
        entry_data = {k.encode(): v.encode() for k, v in serialized.items()}

        stream_key = f"dialogue:{tenant_id}"
        mock_redis.xreadgroup.return_value = [(stream_key.encode(), [(b"1-0", entry_data)])]

        messages = await redis_bus.read_as_consumer(tenant_id, "worker-1")

        assert len(messages) == 1
        entry_id, msg = messages[0]
        assert entry_id == "1-0"
        assert msg.content == "コンシューマーテスト"

    async def test_ack(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """メッセージACKテスト"""
        tenant_id = uuid4()
        result = await redis_bus.ack(tenant_id, ["1-0", "2-0"])

        mock_redis.xack.assert_called_once()
        assert result == 1

    async def test_subscribe_and_notify(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """サブスクライバー通知テスト"""
        callback = AsyncMock()
        to_tenant = uuid4()
        redis_bus.subscribe(str(to_tenant), callback)

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=to_tenant,
            from_agent="test",
            content="通知テスト",
        )
        await redis_bus.send(msg)

        callback.assert_called_once()

    async def test_close(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """接続クローズテスト"""
        await redis_bus.close()

        mock_redis.aclose.assert_called_once()

    async def test_consumer_group_already_exists(self, redis_bus: RedisStreamsBus, mock_redis: AsyncMock) -> None:
        """既存Consumer Groupの場合エラーにならない"""
        mock_redis.xgroup_create.side_effect = Exception("BUSYGROUP")

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="グループ重複テスト",
        )

        # 例外が発生しないことを確認
        result = await redis_bus.send(msg)
        assert result.id is not None


@pytest.mark.unit
class TestCreateDialogueBus:
    """ファクトリ関数テスト"""

    def test_create_memory_bus(self) -> None:
        """インメモリバスの作成"""
        from src.dialogue.bus import DialogueBus, create_dialogue_bus

        bus = create_dialogue_bus(backend="memory")
        assert isinstance(bus, DialogueBus)

    def test_create_redis_bus(self) -> None:
        """Redisバスの作成"""
        from src.dialogue.bus import create_dialogue_bus

        bus = create_dialogue_bus(backend="redis")
        assert isinstance(bus, RedisStreamsBus)

    @patch("src.config.settings.get_settings")
    def test_create_from_settings(self, mock_settings: MagicMock) -> None:
        """設定からバックエンド選択"""
        from src.dialogue.bus import create_dialogue_bus

        mock_settings.return_value.dialogue_bus_backend = "redis"
        bus = create_dialogue_bus()
        assert isinstance(bus, RedisStreamsBus)
