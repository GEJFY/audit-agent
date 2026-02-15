/** 証跡管理 API 関数 */

import { apiClient } from "@/lib/api/client";
import type { EvidenceItem, BoxSearchResult } from "@/types/api";

/** 証跡一覧取得 */
export async function getEvidenceList(params?: {
  project_id?: string;
  source?: string;
  status?: string;
  type?: string;
}): Promise<EvidenceItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set("project_id", params.project_id);
  if (params?.source) searchParams.set("source", params.source);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);

  const query = searchParams.toString();
  const path = `/api/v1/evidence${query ? `?${query}` : ""}`;
  return apiClient.get<EvidenceItem[]>(path);
}

/** 証跡詳細取得 */
export async function getEvidenceById(id: string): Promise<EvidenceItem> {
  return apiClient.get<EvidenceItem>(`/api/v1/evidence/${id}`);
}

/** 証跡ステータス更新 */
export async function updateEvidenceStatus(
  id: string,
  status: "verified" | "rejected",
): Promise<EvidenceItem> {
  return apiClient.put<EvidenceItem>(`/api/v1/evidence/${id}/status`, {
    status,
  });
}

/** 証跡削除 */
export async function deleteEvidence(id: string): Promise<void> {
  return apiClient.delete<void>(`/api/v1/evidence/${id}`);
}

/** Box検索 */
export async function searchBox(
  query: string,
  options?: { folder_id?: string; file_extensions?: string[] },
): Promise<BoxSearchResult[]> {
  return apiClient.post<BoxSearchResult[]>("/api/v1/connectors/box/search", {
    query,
    ...options,
  });
}

/** Box ファイルを証跡としてインポート */
export async function importFromBox(
  fileId: string,
  projectId?: string,
  description?: string,
): Promise<EvidenceItem> {
  return apiClient.post<EvidenceItem>("/api/v1/connectors/box/import", {
    file_id: fileId,
    project_id: projectId,
    description: description || "",
  });
}

/** ファイルサイズのフォーマット */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
