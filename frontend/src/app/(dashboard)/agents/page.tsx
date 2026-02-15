"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bot,
  Play,
  History,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import type {
  AgentInfo,
  AgentDecision,
  AgentExecuteResponse,
} from "@/types/api";

type TabType = "agents" | "decisions";

const agentGroups: Record<string, string> = {
  auditor: "Auditor Agents",
  auditee: "Auditee Agents",
};

function getAgentGroup(name: string): string {
  if (name.startsWith("auditor_")) return "auditor";
  if (name.startsWith("auditee_")) return "auditee";
  return "other";
}

function formatAgentName(name: string): string {
  return name
    .replace(/^(auditor_|auditee_)/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const approvalIcon: Record<string, { icon: typeof Clock; color: string }> = {
  true: { icon: CheckCircle, color: "text-green-500" },
  false: { icon: XCircle, color: "text-red-500" },
  null: { icon: Clock, color: "text-yellow-500" },
};

export default function AgentsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("agents");
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [decisionsTotal, setDecisionsTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AgentExecuteResponse | null>(
    null,
  );
  const [projectId, setProjectId] = useState("");
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await apiClient.get<AgentInfo[]>("/api/v1/agents/");
      setAgents(data);
    } catch {
      // API未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDecisions = useCallback(async () => {
    try {
      const data = await apiClient.get<{
        decisions: AgentDecision[];
        total: number;
      }>("/api/v1/agents/decisions?limit=20");
      setDecisions(data.decisions);
      setDecisionsTotal(data.total);
    } catch {
      // API未接続時は空表示
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchDecisions();
  }, [fetchAgents, fetchDecisions]);

  const handleExecute = async (agentName: string) => {
    setExecuting(agentName);
    setLastResult(null);
    try {
      const result = await apiClient.post<AgentExecuteResponse>(
        "/api/v1/agents/execute",
        {
          agent_name: agentName,
          project_id: projectId || undefined,
        },
      );
      setLastResult(result);
      // 実行後に判断履歴を更新
      fetchDecisions();
    } catch {
      setLastResult({
        agent_name: agentName,
        status: "error",
        message: "Execution failed",
        execution_id: "",
      });
    } finally {
      setExecuting(null);
    }
  };

  // エージェントをグループ分け
  const grouped = agents.reduce(
    (acc, agent) => {
      const group = getAgentGroup(agent.name);
      if (!acc[group]) acc[group] = [];
      acc[group].push(agent);
      return acc;
    },
    {} as Record<string, AgentInfo[]>,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Agents</h2>
        <p className="text-muted-foreground">
          Manage and execute AI audit agents ({agents.length} registered)
        </p>
      </div>

      {/* Execution Result Banner */}
      {lastResult && (
        <Card
          className={`border-l-4 ${lastResult.status === "error" ? "border-l-red-500" : "border-l-green-500"}`}
        >
          <CardContent className="flex items-center gap-3 py-3">
            {lastResult.status === "error" ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : (
              <CheckCircle className="h-5 w-5 text-green-500" />
            )}
            <div>
              <p className="font-medium">
                {formatAgentName(lastResult.agent_name)}: {lastResult.message}
              </p>
              {lastResult.execution_id && (
                <p className="text-xs text-muted-foreground">
                  Execution ID: {lastResult.execution_id}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto"
              onClick={() => setLastResult(null)}
            >
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Project ID Input */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Project ID (optional)"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="max-w-md"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "agents"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("agents")}
        >
          Agents
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "decisions"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("decisions")}
        >
          Decision History ({decisionsTotal})
        </button>
      </div>

      {/* Agents Tab */}
      {activeTab === "agents" && (
        <div className="space-y-6">
          {loading ? (
            <div className="text-center text-muted-foreground py-8">
              Loading...
            </div>
          ) : agents.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Bot className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No agents registered</p>
                <p className="text-sm text-muted-foreground">
                  Start the backend to register agents
                </p>
              </CardContent>
            </Card>
          ) : (
            Object.entries(grouped).map(([group, groupAgents]) => (
              <div key={group}>
                <h3 className="mb-3 text-lg font-semibold">
                  {agentGroups[group] || "Other Agents"}
                </h3>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {groupAgents.map((agent) => (
                    <Card key={agent.name}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center gap-2">
                          <Bot className="h-5 w-5 text-primary" />
                          <CardTitle className="text-base">
                            {formatAgentName(agent.name)}
                          </CardTitle>
                        </div>
                        <CardDescription className="text-xs">
                          {agent.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <span className="rounded bg-muted px-2 py-0.5 text-xs">
                            {agent.name}
                          </span>
                          <Button
                            size="sm"
                            onClick={() => handleExecute(agent.name)}
                            disabled={executing === agent.name}
                          >
                            {executing === agent.name ? (
                              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="mr-1 h-4 w-4" />
                            )}
                            Execute
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Decisions Tab */}
      {activeTab === "decisions" && (
        <div className="space-y-3">
          {decisions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <History className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No decisions yet</p>
                <p className="text-sm text-muted-foreground">
                  Execute an agent to see decision history
                </p>
              </CardContent>
            </Card>
          ) : (
            decisions.map((decision) => {
              const approvalKey = String(decision.human_approved);
              const iconInfo = approvalIcon[approvalKey] || approvalIcon["null"];
              const StatusIcon = iconInfo.icon;
              const isExpanded = expandedDecision === decision.id;

              return (
                <Card key={decision.id}>
                  <CardContent className="py-4">
                    <div
                      className="flex items-center gap-4 cursor-pointer"
                      onClick={() =>
                        setExpandedDecision(isExpanded ? null : decision.id)
                      }
                    >
                      <StatusIcon
                        className={`h-5 w-5 shrink-0 ${iconInfo.color}`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">
                            {formatAgentName(decision.agent_type)}
                          </p>
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                            {decision.decision_type}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                          <span>
                            Confidence:{" "}
                            {(decision.confidence * 100).toFixed(0)}%
                          </span>
                          <span>Model: {decision.model_used}</span>
                          {decision.created_at && (
                            <span>
                              {new Date(decision.created_at).toLocaleString(
                                "ja-JP",
                              )}
                            </span>
                          )}
                        </div>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>

                    {isExpanded && decision.reasoning && (
                      <div className="mt-3 rounded bg-muted p-3 text-sm">
                        <p className="mb-1 font-medium text-xs text-muted-foreground">
                          Reasoning
                        </p>
                        <p className="whitespace-pre-wrap">
                          {decision.reasoning}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
