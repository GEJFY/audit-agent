"""WebSocket エンドポイント — リアルタイム対話・通知"""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from src.api.dependencies import get_current_user_ws

router = APIRouter()


class ConnectionManager:
    """WebSocket接続管理 — テナント×ユーザー単位"""

    def __init__(self) -> None:
        # {tenant_id: {user_id: [websocket, ...]}}
        self._connections: dict[str, dict[str, list[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str) -> None:
        """接続追加"""
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = {}
        if user_id not in self._connections[tenant_id]:
            self._connections[tenant_id][user_id] = []
        self._connections[tenant_id][user_id].append(websocket)
        logger.info("WebSocket接続: tenant={}, user={}", tenant_id, user_id)

    def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str) -> None:
        """接続削除"""
        if tenant_id in self._connections and user_id in self._connections[tenant_id]:
            conns = self._connections[tenant_id][user_id]
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                del self._connections[tenant_id][user_id]
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
        logger.info("WebSocket切断: tenant={}, user={}", tenant_id, user_id)

    async def send_to_user(self, tenant_id: str, user_id: str, data: dict[str, Any]) -> int:
        """特定ユーザーに送信"""
        sent = 0
        conns = self._connections.get(tenant_id, {}).get(user_id, [])
        for ws in conns:
            try:
                await ws.send_json(data)
                sent += 1
            except Exception:
                logger.debug("WebSocket送信エラー (user)")
        return sent

    async def broadcast_to_tenant(self, tenant_id: str, data: dict[str, Any]) -> int:
        """テナント全ユーザーにブロードキャスト"""
        sent = 0
        users = self._connections.get(tenant_id, {})
        for user_conns in users.values():
            for ws in user_conns:
                try:
                    await ws.send_json(data)
                    sent += 1
                except Exception:
                    logger.debug("WebSocket送信エラー (broadcast)")
        return sent

    def get_active_count(self, tenant_id: str | None = None) -> int:
        """アクティブ接続数"""
        if tenant_id:
            return sum(len(conns) for conns in self._connections.get(tenant_id, {}).values())
        return sum(len(conns) for users in self._connections.values() for conns in users.values())


# シングルトン
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """ConnectionManagerを取得"""
    return manager


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
) -> None:
    """WebSocketメインエンドポイント

    クライアントはトークンをクエリパラメータまたは最初のメッセージで送信。

    メッセージ形式:
    送信: {"type": "auth", "token": "..."}
         {"type": "subscribe", "channels": ["dialogue", "alerts"]}
    受信: {"type": "dialogue_message", "data": {...}}
         {"type": "agent_update", "data": {...}}
         {"type": "approval_request", "data": {...}}
         {"type": "risk_alert", "data": {...}}
    """
    # 認証（トークンをクエリパラメータから取得）
    token = websocket.query_params.get("token", "")
    user_info = await get_current_user_ws(token)
    if not user_info:
        await websocket.close(code=4001, reason="認証エラー")
        return

    user_id = user_info.get("user_id", "anonymous")
    await manager.connect(websocket, tenant_id, user_id)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "不正なJSON"})
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "subscribe":
                channels = data.get("channels", [])
                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "channels": channels,
                    }
                )

            elif msg_type == "dialogue_send":
                # Dialogue Busへメッセージ送信
                result = await _handle_dialogue_send(data, tenant_id, user_id)
                await websocket.send_json(result)

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"不明なメッセージタイプ: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id, user_id)
    except Exception as e:
        logger.error("WebSocketエラー: {}", str(e))
        manager.disconnect(websocket, tenant_id, user_id)


async def _handle_dialogue_send(data: dict[str, Any], tenant_id: str, user_id: str) -> dict[str, Any]:
    """WebSocket経由の対話メッセージ送信"""
    content = data.get("content", "")
    to_tenant = data.get("to_tenant_id", "")

    if not content or not to_tenant:
        return {"type": "error", "message": "content, to_tenant_idが必要です"}

    # DialogueBusに送信
    from src.config.constants import DialogueMessageType
    from src.dialogue.bus import DialogueBus
    from src.dialogue.protocol import DialogueMessageSchema

    bus = DialogueBus()
    try:
        message = DialogueMessageSchema(
            from_tenant_id=UUID(tenant_id),
            to_tenant_id=UUID(to_tenant),
            from_agent=f"user:{user_id}",
            message_type=DialogueMessageType(data.get("message_type", "question")),
            content=content,
            subject=data.get("subject"),
        )
        sent = await bus.send(message)

        # 相手テナントにリアルタイム通知
        await manager.broadcast_to_tenant(
            to_tenant,
            {
                "type": "dialogue_message",
                "data": {
                    "id": str(sent.id),
                    "from_tenant_id": tenant_id,
                    "content": content[:200],
                    "message_type": sent.message_type.value,
                    "timestamp": sent.timestamp.isoformat(),
                },
            },
        )

        return {"type": "dialogue_sent", "message_id": str(sent.id)}
    except Exception as e:
        return {"type": "error", "message": str(e)}
