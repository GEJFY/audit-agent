/** プロジェクト管理 API 関数 */

import type {
  AuditProject,
  AgentDecision,
  ApprovalQueueItem,
} from "@/types/api";
import { apiClient } from "./client";

// ── Project CRUD ────────────────────────────────
export interface ProjectListParams {
  status?: string;
  fiscal_year?: number;
  offset?: number;
  limit?: number;
}

interface ProjectListResponse {
  projects: AuditProject[];
  total: number;
}

export async function getProjects(
  params?: ProjectListParams,
): Promise<ProjectListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.fiscal_year)
    query.set("fiscal_year", String(params.fiscal_year));
  if (params?.offset) query.set("offset", String(params.offset));
  if (params?.limit) query.set("limit", String(params.limit));

  const qs = query.toString();
  return apiClient.get<ProjectListResponse>(
    `/api/v1/projects/${qs ? `?${qs}` : ""}`,
  );
}

export interface ProjectCreateInput {
  name: string;
  description: string;
  project_type: string;
  fiscal_year: number;
  department: string;
}

export async function createProject(
  input: ProjectCreateInput,
): Promise<AuditProject> {
  return apiClient.post<AuditProject>("/api/v1/projects/", input);
}

export async function getProject(projectId: string): Promise<AuditProject> {
  return apiClient.get<AuditProject>(`/api/v1/projects/${projectId}`);
}

export async function updateProject(
  projectId: string,
  input: Partial<ProjectCreateInput> & { status?: string },
): Promise<AuditProject> {
  return apiClient.put<AuditProject>(`/api/v1/projects/${projectId}`, input);
}

export async function deleteProject(projectId: string): Promise<void> {
  return apiClient.delete(`/api/v1/projects/${projectId}`);
}

// ── Dashboard Stats ─────────────────────────────
export interface DashboardStats {
  activeProjects: number;
  pendingApprovals: number;
  agentDecisions: number;
  riskAlerts: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  // 複数のAPIを並行して呼び出してダッシュボード統計を構築
  const [projects, approvals, decisions] = await Promise.allSettled([
    getProjects({ limit: 100 }),
    apiClient.get<ApprovalQueueItem[]>("/api/v1/agents/approval-queue"),
    apiClient.get<{ decisions: AgentDecision[]; total: number }>(
      "/api/v1/agents/decisions?limit=10",
    ),
  ]);

  return {
    activeProjects:
      projects.status === "fulfilled"
        ? projects.value.projects.filter(
            (p) => p.status !== "completed" && p.status !== "draft",
          ).length
        : 0,
    pendingApprovals:
      approvals.status === "fulfilled" ? approvals.value.length : 0,
    agentDecisions:
      decisions.status === "fulfilled" ? decisions.value.total : 0,
    riskAlerts: 0, // Phase 1 では未実装
  };
}
