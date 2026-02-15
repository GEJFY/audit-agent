/** 統制スコアカード & リスクダッシュボード API */

import type {
  ControlScorecard,
  ControlScore,
  RiskDashboardData,
  RiskItem,
} from "@/types/api";
import { apiClient } from "./client";

// ── Controls ────────────────────────────────────

export async function getControlScorecard(
  projectId?: string,
): Promise<ControlScorecard> {
  const query = projectId ? `?project_id=${projectId}` : "";
  try {
    return await apiClient.get<ControlScorecard>(
      `/api/v1/controls/scorecard${query}`,
    );
  } catch {
    // API未実装時はデモデータを返す
    return generateDemoScorecard();
  }
}

export async function getControls(
  params?: { category?: string; status?: string; project_id?: string },
): Promise<ControlScore[]> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.status) query.set("status", params.status);
  if (params?.project_id) query.set("project_id", params.project_id);
  const qs = query.toString();
  try {
    return await apiClient.get<ControlScore[]>(
      `/api/v1/controls/${qs ? `?${qs}` : ""}`,
    );
  } catch {
    return generateDemoScorecard().controls;
  }
}

// ── Risk ─────────────────────────────────────────

export async function getRiskDashboard(
  projectId?: string,
): Promise<RiskDashboardData> {
  const query = projectId ? `?project_id=${projectId}` : "";
  try {
    return await apiClient.get<RiskDashboardData>(
      `/api/v1/risk/dashboard${query}`,
    );
  } catch {
    return generateDemoRiskData();
  }
}

export async function getRisks(
  params?: { level?: string; status?: string; category?: string },
): Promise<RiskItem[]> {
  const query = new URLSearchParams();
  if (params?.level) query.set("level", params.level);
  if (params?.status) query.set("status", params.status);
  if (params?.category) query.set("category", params.category);
  const qs = query.toString();
  try {
    return await apiClient.get<RiskItem[]>(
      `/api/v1/risk/${qs ? `?${qs}` : ""}`,
    );
  } catch {
    return generateDemoRiskData().recent_risks;
  }
}

// ── Demo Data (APIエンドポイント未実装時) ────────

function generateDemoScorecard(): ControlScorecard {
  const controls: ControlScore[] = [
    {
      id: "ctrl-001", control_id: "AC-001", control_name: "Access Control Review",
      category: "Access Control", description: "Periodic review of user access rights",
      score: 92, status: "effective", last_tested: "2026-02-10T09:00:00Z",
      tester_agent: "controls_tester", findings_count: 0,
      remediation_status: "none", project_id: null,
    },
    {
      id: "ctrl-002", control_id: "AC-002", control_name: "Segregation of Duties",
      category: "Access Control", description: "Ensure proper SoD across financial systems",
      score: 78, status: "partially_effective", last_tested: "2026-02-08T14:00:00Z",
      tester_agent: "controls_tester", findings_count: 2,
      remediation_status: "in_progress", project_id: null,
    },
    {
      id: "ctrl-003", control_id: "FP-001", control_name: "Journal Entry Approval",
      category: "Financial Process", description: "Dual approval for journal entries over threshold",
      score: 95, status: "effective", last_tested: "2026-02-12T10:00:00Z",
      tester_agent: "controls_tester", findings_count: 0,
      remediation_status: "none", project_id: null,
    },
    {
      id: "ctrl-004", control_id: "FP-002", control_name: "Bank Reconciliation",
      category: "Financial Process", description: "Monthly bank account reconciliation",
      score: 88, status: "effective", last_tested: "2026-02-01T08:00:00Z",
      tester_agent: "controls_tester", findings_count: 1,
      remediation_status: "completed", project_id: null,
    },
    {
      id: "ctrl-005", control_id: "IT-001", control_name: "Change Management",
      category: "IT General Controls", description: "IT change request and approval process",
      score: 65, status: "partially_effective", last_tested: "2026-02-05T11:00:00Z",
      tester_agent: "controls_tester", findings_count: 3,
      remediation_status: "in_progress", project_id: null,
    },
    {
      id: "ctrl-006", control_id: "IT-002", control_name: "Backup & Recovery",
      category: "IT General Controls", description: "Regular backup and disaster recovery testing",
      score: 45, status: "ineffective", last_tested: "2026-01-20T15:00:00Z",
      tester_agent: "controls_tester", findings_count: 4,
      remediation_status: "overdue", project_id: null,
    },
    {
      id: "ctrl-007", control_id: "CM-001", control_name: "Vendor Due Diligence",
      category: "Compliance", description: "Third-party vendor risk assessment",
      score: 82, status: "effective", last_tested: "2026-02-11T09:30:00Z",
      tester_agent: "controls_tester", findings_count: 1,
      remediation_status: "none", project_id: null,
    },
    {
      id: "ctrl-008", control_id: "CM-002", control_name: "Regulatory Reporting",
      category: "Compliance", description: "Timely and accurate regulatory submissions",
      score: 0, status: "not_tested", last_tested: null,
      tester_agent: null, findings_count: 0,
      remediation_status: "none", project_id: null,
    },
  ];

  const effective = controls.filter((c) => c.status === "effective").length;
  const partial = controls.filter((c) => c.status === "partially_effective").length;
  const ineffective = controls.filter((c) => c.status === "ineffective").length;
  const notTested = controls.filter((c) => c.status === "not_tested").length;
  const testedControls = controls.filter((c) => c.status !== "not_tested");
  const overall = testedControls.length > 0
    ? Math.round(testedControls.reduce((sum, c) => sum + c.score, 0) / testedControls.length)
    : 0;

  const byCategory: Record<string, { score: number; count: number }> = {};
  for (const c of controls) {
    if (!byCategory[c.category]) byCategory[c.category] = { score: 0, count: 0 };
    byCategory[c.category].count++;
    byCategory[c.category].score += c.score;
  }
  for (const cat of Object.keys(byCategory)) {
    byCategory[cat].score = Math.round(byCategory[cat].score / byCategory[cat].count);
  }

  return {
    overall_score: overall,
    total_controls: controls.length,
    effective,
    partially_effective: partial,
    ineffective,
    not_tested: notTested,
    by_category: byCategory,
    controls,
  };
}

function generateDemoRiskData(): RiskDashboardData {
  const risks: RiskItem[] = [
    {
      id: "risk-001", title: "Unauthorized Access Pattern Detected",
      description: "Anomalous login patterns from SAP system detected by ML model",
      risk_level: "critical", risk_score: 92, category: "Access Control",
      source: "anomaly_detective", detected_at: "2026-02-14T16:30:00Z",
      status: "open", project_id: null,
    },
    {
      id: "risk-002", title: "Journal Entry Threshold Bypass",
      description: "Multiple journal entries just below approval threshold",
      risk_level: "high", risk_score: 78, category: "Financial Process",
      source: "anomaly_detective", detected_at: "2026-02-13T10:15:00Z",
      status: "open", project_id: null,
    },
    {
      id: "risk-003", title: "IT Change Without Approval",
      description: "Production changes deployed without proper change management approval",
      risk_level: "high", risk_score: 75, category: "IT General Controls",
      source: "controls_tester", detected_at: "2026-02-12T14:45:00Z",
      status: "mitigated", project_id: null,
    },
    {
      id: "risk-004", title: "Backup Failure - 3 Consecutive",
      description: "Database backup has failed for 3 consecutive days",
      risk_level: "high", risk_score: 70, category: "IT General Controls",
      source: "controls_tester", detected_at: "2026-02-10T08:00:00Z",
      status: "open", project_id: null,
    },
    {
      id: "risk-005", title: "Vendor Contract Expiration",
      description: "Critical vendor contract expiring without renewal process initiated",
      risk_level: "medium", risk_score: 55, category: "Compliance",
      source: "knowledge_agent", detected_at: "2026-02-09T11:00:00Z",
      status: "accepted", project_id: null,
    },
    {
      id: "risk-006", title: "Duplicate Payment Detection",
      description: "Potential duplicate payment identified in AP system",
      risk_level: "medium", risk_score: 50, category: "Financial Process",
      source: "anomaly_detective", detected_at: "2026-02-08T09:30:00Z",
      status: "closed", project_id: null,
    },
    {
      id: "risk-007", title: "Weak Password Policy Compliance",
      description: "15% of users not compliant with updated password policy",
      risk_level: "low", risk_score: 30, category: "Access Control",
      source: "controls_tester", detected_at: "2026-02-07T13:00:00Z",
      status: "mitigated", project_id: null,
    },
  ];

  return {
    total_risks: risks.length,
    critical: risks.filter((r) => r.risk_level === "critical").length,
    high: risks.filter((r) => r.risk_level === "high").length,
    medium: risks.filter((r) => r.risk_level === "medium").length,
    low: risks.filter((r) => r.risk_level === "low").length,
    open_risks: risks.filter((r) => r.status === "open").length,
    mitigated_risks: risks.filter((r) => r.status === "mitigated").length,
    risk_trend: [
      { date: "2026-02-09", score: 68, count: 3 },
      { date: "2026-02-10", score: 72, count: 4 },
      { date: "2026-02-11", score: 70, count: 4 },
      { date: "2026-02-12", score: 74, count: 5 },
      { date: "2026-02-13", score: 71, count: 6 },
      { date: "2026-02-14", score: 75, count: 7 },
      { date: "2026-02-15", score: 73, count: 7 },
    ],
    by_category: {
      "Access Control": 2,
      "Financial Process": 2,
      "IT General Controls": 2,
      "Compliance": 1,
    },
    recent_risks: risks,
  };
}
