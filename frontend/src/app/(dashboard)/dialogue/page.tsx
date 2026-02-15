"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Send,
  Bot,
  User,
  Wifi,
  WifiOff,
  MessageSquare,
  AlertCircle,
  HelpCircle,
  ArrowRightLeft,
  ChevronRight,
} from "lucide-react";

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
import {
  sendMessage,
  getRecentMessages,
  getThreads,
} from "@/lib/api/dialogue";
import type { DialogueMessage, DialogueThread } from "@/types/api";

const messageTypeConfig: Record<
  DialogueMessage["message_type"],
  { icon: typeof MessageSquare; color: string; label: string }
> = {
  question: { icon: HelpCircle, color: "text-blue-500", label: "Question" },
  answer: { icon: MessageSquare, color: "text-green-500", label: "Answer" },
  clarification: { icon: ArrowRightLeft, color: "text-yellow-500", label: "Clarification" },
  escalation: { icon: AlertCircle, color: "text-red-500", label: "Escalation" },
};

const threadStatusColor: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  resolved: "bg-gray-100 text-gray-600",
  escalated: "bg-red-100 text-red-700",
};

export default function DialoguePage() {
  const user = useAuthStore((state) => state.user);
  const [messages, setMessages] = useState<DialogueMessage[]>([]);
  const [threads, setThreads] = useState<DialogueThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [messageType, setMessageType] = useState<DialogueMessage["message_type"]>("question");
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [msgs, threadList] = await Promise.allSettled([
          getRecentMessages(50),
          getThreads(),
        ]);
        if (msgs.status === "fulfilled") setMessages(msgs.value);
        if (threadList.status === "fulfilled") setThreads(threadList.value);
      } catch {
        // API未接続時
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    setSending(true);
    try {
      const msg = await sendMessage({
        from_agent: "human",
        message_type: messageType,
        content: inputValue.trim(),
        thread_id: selectedThread || undefined,
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

  const formatDate = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleDateString("en", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  const isHuman = (msg: DialogueMessage) =>
    msg.from_agent === "human" || msg.from_agent === "user";

  const filteredMessages = selectedThread
    ? messages.filter((m) => m.thread_id === selectedThread)
    : messages;

  const qualityColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* Thread Sidebar */}
      <div className="w-72 flex-shrink-0 overflow-hidden rounded-lg border bg-card">
        <div className="border-b p-3">
          <h3 className="font-semibold text-sm">Threads</h3>
          <p className="text-xs text-muted-foreground">
            {threads.length} conversations
          </p>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: "calc(100% - 56px)" }}>
          {/* All Messages */}
          <button
            className={cn(
              "w-full border-b px-3 py-2.5 text-left transition-colors hover:bg-muted/50",
              !selectedThread && "bg-primary/5 border-l-2 border-l-primary",
            )}
            onClick={() => setSelectedThread(null)}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">All Messages</span>
              <span className="text-xs text-muted-foreground">
                {messages.length}
              </span>
            </div>
          </button>

          {threads.map((thread) => (
            <button
              key={thread.thread_id}
              className={cn(
                "w-full border-b px-3 py-2.5 text-left transition-colors hover:bg-muted/50",
                selectedThread === thread.thread_id &&
                  "bg-primary/5 border-l-2 border-l-primary",
              )}
              onClick={() => setSelectedThread(thread.thread_id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {thread.subject}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {thread.participants.slice(0, 2).join(", ")}
                    {thread.participants.length > 2 &&
                      ` +${thread.participants.length - 2}`}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span
                    className={cn(
                      "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                      threadStatusColor[thread.status] || "bg-gray-100",
                    )}
                  >
                    {thread.status}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {thread.message_count} msgs
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              {selectedThread
                ? threads.find((t) => t.thread_id === selectedThread)?.subject ||
                  "Thread"
                : "All Messages"}
            </h2>
            <p className="text-sm text-muted-foreground">
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
          {filteredMessages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              {selectedThread
                ? "No messages in this thread yet."
                : "No messages yet. Start a conversation with the AI agents."}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredMessages.map((msg) => {
                const typeConfig = messageTypeConfig[msg.message_type];
                const TypeIcon = typeConfig?.icon || MessageSquare;
                return (
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
                        msg.message_type === "escalation" &&
                          !isHuman(msg) &&
                          "border-l-2 border-l-red-500",
                      )}
                    >
                      <CardContent className="p-3">
                        <div className="mb-1 flex items-center gap-2">
                          <span className="text-xs font-medium opacity-70">
                            {msg.from_agent}
                          </span>
                          <TypeIcon
                            className={cn(
                              "h-3 w-3",
                              isHuman(msg) ? "opacity-60" : typeConfig?.color,
                            )}
                          />
                          <span
                            className={cn(
                              "text-[10px]",
                              isHuman(msg) ? "opacity-50" : "opacity-60",
                            )}
                          >
                            {typeConfig?.label}
                          </span>
                          {msg.quality_score !== null && !isHuman(msg) && (
                            <span
                              className={cn(
                                "text-[10px] font-medium",
                                qualityColor(msg.quality_score),
                              )}
                            >
                              Q:{(msg.quality_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        <p className="whitespace-pre-wrap text-sm">
                          {msg.content}
                        </p>
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
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t pt-3">
          <div className="mb-2 flex gap-1">
            {(
              ["question", "answer", "clarification", "escalation"] as const
            ).map((type) => {
              const cfg = messageTypeConfig[type];
              const Icon = cfg.icon;
              return (
                <button
                  key={type}
                  className={cn(
                    "flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors",
                    messageType === type
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-muted",
                  )}
                  onClick={() => setMessageType(type)}
                >
                  <Icon className="h-3 w-3" />
                  {cfg.label}
                </button>
              );
            })}
          </div>
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message to the AI agents..."
              disabled={sending}
            />
            <Button
              onClick={handleSend}
              disabled={sending || !inputValue.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
