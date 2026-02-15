/** エージェント管理 API 関数 */

import { apiClient } from "@/lib/api/client";
import type {
  AgentInfo,
  AgentDecision,
  AgentExecuteRequest,
  AgentExecuteResponse,
} from "@/types/api";

/** 登録済みエージェント一覧取得 */
export async function getAgents(): Promise<AgentInfo[]> {
  return apiClient.get<AgentInfo[]>("/api/v1/agents/");
}

/** エージェント実行 */
export async function executeAgent(
  request: AgentExecuteRequest,
): Promise<AgentExecuteResponse> {
  return apiClient.post<AgentExecuteResponse>(
    "/api/v1/agents/execute",
    request,
  );
}

/** エージェント判断履歴取得 */
export async function getDecisions(params?: {
  decision_status?: string;
  agent_type?: string;
  offset?: number;
  limit?: number;
}): Promise<{ decisions: AgentDecision[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.decision_status)
    searchParams.set("decision_status", params.decision_status);
  if (params?.agent_type) searchParams.set("agent_type", params.agent_type);
  if (params?.offset !== undefined)
    searchParams.set("offset", String(params.offset));
  if (params?.limit !== undefined)
    searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  const path = `/api/v1/agents/decisions${query ? `?${query}` : ""}`;
  return apiClient.get<{ decisions: AgentDecision[]; total: number }>(path);
}
