/** WebSocket フック — リアルタイム対話メッセージ受信 */

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api/client";

export interface WSMessage {
  type: string;
  data: Record<string, unknown>;
}

interface UseWebSocketOptions {
  tenantId: string;
  onMessage?: (message: WSMessage) => void;
  autoConnect?: boolean;
}

export function useWebSocket({
  tenantId,
  onMessage,
  autoConnect = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const token = apiClient.getAccessToken();
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = process.env.NEXT_PUBLIC_WS_URL || `${wsProtocol}//localhost:8000`;
    const url = `${wsHost}/ws/${tenantId}${token ? `?token=${token}` : ""}`;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        setLastMessage(message);
        onMessage?.(message);
      } catch {
        // non-JSON message
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // 自動再接続（5秒後）
      reconnectTimeoutRef.current = setTimeout(() => {
        if (autoConnect) connect();
      }, 5000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [tenantId, onMessage, autoConnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const send = useCallback((data: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    if (autoConnect) connect();
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  return { isConnected, lastMessage, connect, disconnect, send };
}
