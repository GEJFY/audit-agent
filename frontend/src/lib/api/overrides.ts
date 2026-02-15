/** Human Override API */

import type { HumanOverride } from "@/types/api";
import { apiClient } from "./client";

export interface CreateOverrideInput {
  decision_id: string;
  override_action: string;
  reason: string;
}

export async function createOverride(
  input: CreateOverrideInput,
): Promise<HumanOverride> {
  try {
    return await apiClient.post<HumanOverride>(
      "/api/v1/agents/override",
      input,
    );
  } catch {
    // API未実装時はデモレスポンス
    return {
      id: `override-${Date.now()}`,
      decision_id: input.decision_id,
      agent_type: "unknown",
      original_action: "auto_execute",
      override_action: input.override_action,
      reason: input.reason,
      overridden_by: "current_user",
      created_at: new Date().toISOString(),
    };
  }
}

export async function getOverrides(
  params?: { decision_id?: string },
): Promise<HumanOverride[]> {
  const query = params?.decision_id
    ? `?decision_id=${params.decision_id}`
    : "";
  try {
    return await apiClient.get<HumanOverride[]>(
      `/api/v1/agents/overrides${query}`,
    );
  } catch {
    return generateDemoOverrides();
  }
}

function generateDemoOverrides(): HumanOverride[] {
  return [
    {
      id: "ovr-001",
      decision_id: "dec-101",
      agent_type: "anomaly_detective",
      original_action: "flag_as_anomaly",
      override_action: "dismiss",
      reason:
        "False positive - this is a regular year-end adjustment entry",
      overridden_by: "tanaka@example.com",
      created_at: "2026-02-14T15:30:00Z",
    },
    {
      id: "ovr-002",
      decision_id: "dec-102",
      agent_type: "controls_tester",
      original_action: "mark_effective",
      override_action: "mark_partially_effective",
      reason:
        "Control is effective for most cases but has a gap in manual override scenarios",
      overridden_by: "suzuki@example.com",
      created_at: "2026-02-13T10:15:00Z",
    },
    {
      id: "ovr-003",
      decision_id: "dec-103",
      agent_type: "risk_scorer",
      original_action: "score_low",
      override_action: "score_high",
      reason:
        "Risk score should be elevated due to upcoming regulatory changes",
      overridden_by: "tanaka@example.com",
      created_at: "2026-02-12T09:45:00Z",
    },
  ];
}
