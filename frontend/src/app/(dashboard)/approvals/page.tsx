"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, X, Clock, AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type { ApprovalQueueItem, AgentDecision } from "@/types/api";

const priorityColor: Record<string, string> = {
  high: "border-l-red-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

const priorityIcon: Record<string, typeof AlertTriangle> = {
  high: AlertTriangle,
  medium: Clock,
  low: Clock,
};

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    try {
      const data = await apiClient.get<ApprovalQueueItem[]>(
        "/api/v1/agents/approval-queue",
      );
      setItems(data);
    } catch {
      // API未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleAction = async (
    decisionId: string,
    action: "approved" | "rejected",
  ) => {
    setActionLoading(decisionId);
    try {
      await apiClient.post(`/api/v1/agents/decisions/${decisionId}/approve`, {
        action,
        comment: "",
      });
      // 承認/却下後にリスト更新
      setItems((prev) =>
        prev.filter((item) => item.decision_id !== decisionId),
      );
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Approvals</h2>
        <p className="text-muted-foreground">
          Review and approve AI agent decisions ({items.length} pending)
        </p>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Check className="mb-4 h-12 w-12 text-green-500" />
            <p className="text-lg font-medium">All caught up!</p>
            <p className="text-sm text-muted-foreground">
              No pending approvals
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const PriorityIcon =
              priorityIcon[item.priority] || Clock;
            return (
              <Card
                key={item.id}
                className={`border-l-4 ${priorityColor[item.priority] || "border-l-gray-300"}`}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PriorityIcon className="h-4 w-4" />
                      <CardTitle className="text-base">
                        {item.approval_type}
                      </CardTitle>
                    </div>
                    <span className="text-xs text-muted-foreground capitalize">
                      {item.priority} priority
                    </span>
                  </div>
                  <CardDescription>
                    Requested by: {item.requested_by_agent}
                    {item.created_at && (
                      <> &middot; {new Date(item.created_at).toLocaleString("ja-JP")}</>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {item.context && Object.keys(item.context).length > 0 && (
                    <div className="mb-4 rounded bg-muted p-3 text-sm">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(item.context, null, 2)}
                      </pre>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() =>
                        handleAction(item.decision_id, "approved")
                      }
                      disabled={actionLoading === item.decision_id}
                    >
                      <Check className="mr-1 h-4 w-4" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() =>
                        handleAction(item.decision_id, "rejected")
                      }
                      disabled={actionLoading === item.decision_id}
                    >
                      <X className="mr-1 h-4 w-4" />
                      Reject
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
