"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Bot, User, Wifi, WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useWebSocket, type WSMessage } from "@/hooks/use-websocket";
import { sendMessage, getRecentMessages } from "@/lib/api/dialogue";
import type { DialogueMessage } from "@/types/api";

export default function DialoguePage() {
  const user = useAuthStore((state) => state.user);
  const [messages, setMessages] = useState<DialogueMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === "dialogue_message" && msg.data) {
      setMessages((prev) => [...prev, msg.data as unknown as DialogueMessage]);
    }
  }, []);

  const { isConnected } = useWebSocket({
    tenantId: user?.tenant_id || "default",
    onMessage: handleWSMessage,
    autoConnect: !!user?.tenant_id,
  });

  // 初回メッセージ読み込み
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const msgs = await getRecentMessages(50);
        setMessages(msgs);
      } catch {
        // API未接続時は空表示
      }
    };
    fetchMessages();
  }, []);

  // 自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    setSending(true);
    try {
      const msg = await sendMessage({
        from_agent: "human",
        message_type: "question",
        content: inputValue.trim(),
      });
      setMessages((prev) => [...prev, msg]);
      setInputValue("");
    } catch {
      // エラーハンドリング
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString("ja-JP", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  const isHuman = (msg: DialogueMessage) =>
    msg.from_agent === "human" || msg.from_agent === "user";

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dialogue</h2>
          <p className="text-muted-foreground">
            AI Agent Communication
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-green-600">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-gray-400" />
              <span className="text-muted-foreground">Disconnected</span>
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            No messages yet. Start a conversation with the AI agents.
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "flex gap-3",
                  isHuman(msg) ? "justify-end" : "justify-start",
                )}
              >
                {!isHuman(msg) && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <Card
                  className={cn(
                    "max-w-[70%]",
                    isHuman(msg)
                      ? "bg-primary text-primary-foreground"
                      : "bg-card",
                  )}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium opacity-70">
                        {msg.from_agent}
                      </span>
                      {msg.quality_score !== null && (
                        <span className="text-xs opacity-50">
                          Score: {msg.quality_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    <span className="mt-1 block text-xs opacity-50">
                      {formatTime(msg.timestamp)}
                    </span>
                  </CardContent>
                </Card>
                {isHuman(msg) && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t pt-4">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message to the AI agents..."
            disabled={sending}
          />
          <Button onClick={handleSend} disabled={sending || !inputValue.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
