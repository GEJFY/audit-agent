"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check,
  X,
  Clock,
  AlertTriangle,
  RotateCcw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { createOverride, getOverrides } from "@/lib/api/overrides";
import type { ApprovalQueueItem, HumanOverride } from "@/types/api";

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

type TabType = "pending" | "overrides";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalQueueItem[]>([]);
  const [overrides, setOverrides] = useState<HumanOverride[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("pending");

  // Rejection/Override state
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [overrideAction, setOverrideAction] = useState("");
  const [expandedContext, setExpandedContext] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    try {
      const [approvals, overrideList] = await Promise.allSettled([
        apiClient.get<ApprovalQueueItem[]>("/api/v1/agents/approval-queue"),
        getOverrides(),
      ]);
      if (approvals.status === "fulfilled") setItems(approvals.value);
      if (overrideList.status === "fulfilled") setOverrides(overrideList.value);
    } catch {
      // API未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApprove = async (decisionId: string) => {
    setActionLoading(decisionId);
    try {
      await apiClient.post(`/api/v1/agents/decisions/${decisionId}/approve`, {
        action: "approved",
        comment: "",
      });
      setItems((prev) =>
        prev.filter((item) => item.decision_id !== decisionId),
      );
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const handleRejectWithReason = async (decisionId: string) => {
    if (!rejectReason.trim()) return;
    setActionLoading(decisionId);
    try {
      await apiClient.post(`/api/v1/agents/decisions/${decisionId}/approve`, {
        action: "rejected",
        comment: rejectReason,
      });
      setItems((prev) =>
        prev.filter((item) => item.decision_id !== decisionId),
      );
      setRejectingId(null);
      setRejectReason("");
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const handleOverride = async (decisionId: string) => {
    if (!overrideAction.trim() || !rejectReason.trim()) return;
    setActionLoading(decisionId);
    try {
      const newOverride = await createOverride({
        decision_id: decisionId,
        override_action: overrideAction,
        reason: rejectReason,
      });
      setOverrides((prev) => [newOverride, ...prev]);
      setItems((prev) =>
        prev.filter((item) => item.decision_id !== decisionId),
      );
      setRejectingId(null);
      setRejectReason("");
      setOverrideAction("");
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const tabs: { key: TabType; label: string; count: number }[] = [
    { key: "pending", label: "Pending Approvals", count: items.length },
    { key: "overrides", label: "Override History", count: overrides.length },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">
          Approvals & Overrides
        </h2>
        <p className="text-muted-foreground">
          Review agent decisions, approve or override with human judgment
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Pending Approvals Tab */}
      {activeTab === "pending" && (
        <>
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
                const PriorityIcon = priorityIcon[item.priority] || Clock;
                const isRejecting = rejectingId === item.decision_id;
                const isExpanded = expandedContext === item.id;
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
                          <>
                            {" "}
                            &middot;{" "}
                            {new Date(item.created_at).toLocaleString("ja-JP")}
                          </>
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {/* Context (collapsible) */}
                      {item.context &&
                        Object.keys(item.context).length > 0 && (
                          <div className="mb-4">
                            <button
                              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                              onClick={() =>
                                setExpandedContext(isExpanded ? null : item.id)
                              }
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-3 w-3" />
                              ) : (
                                <ChevronDown className="h-3 w-3" />
                              )}
                              Decision Context
                            </button>
                            {isExpanded && (
                              <div className="mt-2 rounded bg-muted p-3 text-sm">
                                <pre className="whitespace-pre-wrap text-xs">
                                  {JSON.stringify(item.context, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}

                      {/* Rejection/Override Form */}
                      {isRejecting ? (
                        <div className="space-y-3 rounded-md border bg-muted/50 p-3">
                          <div>
                            <label className="mb-1 block text-xs font-medium">
                              Override Action (optional)
                            </label>
                            <Input
                              value={overrideAction}
                              onChange={(e) =>
                                setOverrideAction(e.target.value)
                              }
                              placeholder="e.g., dismiss, mark_partially_effective, score_high"
                              className="text-sm"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs font-medium">
                              Reason *
                            </label>
                            <textarea
                              value={rejectReason}
                              onChange={(e) =>
                                setRejectReason(e.target.value)
                              }
                              placeholder="Explain why you are rejecting or overriding this decision..."
                              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                              rows={3}
                            />
                          </div>
                          <div className="flex gap-2">
                            {overrideAction.trim() ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  handleOverride(item.decision_id)
                                }
                                disabled={
                                  !rejectReason.trim() ||
                                  actionLoading === item.decision_id
                                }
                              >
                                <RotateCcw className="mr-1 h-4 w-4" />
                                Override
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() =>
                                  handleRejectWithReason(item.decision_id)
                                }
                                disabled={
                                  !rejectReason.trim() ||
                                  actionLoading === item.decision_id
                                }
                              >
                                <X className="mr-1 h-4 w-4" />
                                Reject
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setRejectingId(null);
                                setRejectReason("");
                                setOverrideAction("");
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleApprove(item.decision_id)}
                            disabled={actionLoading === item.decision_id}
                          >
                            <Check className="mr-1 h-4 w-4" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() =>
                              setRejectingId(item.decision_id)
                            }
                            disabled={actionLoading === item.decision_id}
                          >
                            <X className="mr-1 h-4 w-4" />
                            Reject / Override
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Override History Tab */}
      {activeTab === "overrides" && (
        <>
          {overrides.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <RotateCcw className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No overrides yet</p>
                <p className="text-sm text-muted-foreground">
                  Human override history will appear here
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {overrides.map((ovr) => (
                <Card key={ovr.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <RotateCcw className="h-4 w-4 text-orange-500" />
                          <span className="text-sm font-medium">
                            {ovr.agent_type}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            Decision: {ovr.decision_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="rounded bg-red-50 px-1.5 py-0.5 text-red-600 line-through">
                            {ovr.original_action}
                          </span>
                          <span className="text-muted-foreground">&rarr;</span>
                          <span className="rounded bg-green-50 px-1.5 py-0.5 text-green-600 font-medium">
                            {ovr.override_action}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {ovr.reason}
                        </p>
                      </div>
                      <div className="ml-4 text-right text-xs text-muted-foreground">
                        <p>{ovr.overridden_by}</p>
                        <p>
                          {new Date(ovr.created_at).toLocaleDateString("ja-JP")}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
