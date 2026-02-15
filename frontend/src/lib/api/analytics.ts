/** Analytics API クライアント — ポートフォリオ・ベンチマーク */

import type {
  PortfolioSummary,
  PortfolioCompany,
  BenchmarkResult,
  AutonomousStats,
  AutonomousDecision,
} from "@/types/api";

// ── デモデータ ────────────────────────────────────
const DEMO_PORTFOLIO: PortfolioSummary = {
  total_companies: 12,
  avg_overall_score: 58.3,
  risk_distribution: { critical: 1, high: 3, medium: 5, low: 3 },
  industry_distribution: { finance: 5, manufacturing: 4, it_services: 3 },
  alerts_count: 2,
  alerts: [
    {
      alert_type: "threshold_breach",
      severity: "critical",
      description: "1社がクリティカルリスクレベル",
      affected_companies: ["C001"],
    },
    {
      alert_type: "concentration_risk",
      severity: "high",
      description: "'finance'業種に高リスク企業が集中（3/12社）",
      affected_companies: ["C001", "C003", "C005"],
    },
  ],
  category_averages: {
    financial_process: 62.5,
    access_control: 55.0,
    it_general: 48.2,
    inventory: 42.0,
  },
};

const DEMO_COMPANIES: PortfolioCompany[] = [
  {
    company_id: "C001",
    company_name: "金融A社",
    industry: "finance",
    region: "JP",
    overall_score: 82,
    risk_level: "critical",
    category_scores: { financial_process: 90, access_control: 75, it_general: 70 },
    trend: "worsening",
    open_findings: 8,
  },
  {
    company_id: "C002",
    company_name: "金融B社",
    industry: "finance",
    region: "JP",
    overall_score: 55,
    risk_level: "medium",
    category_scores: { financial_process: 60, access_control: 50, it_general: 45 },
    trend: "stable",
    open_findings: 3,
  },
  {
    company_id: "C003",
    company_name: "製造A社",
    industry: "manufacturing",
    region: "JP",
    overall_score: 68,
    risk_level: "high",
    category_scores: { inventory: 72, quality: 65, financial_process: 58 },
    trend: "improving",
    open_findings: 5,
  },
  {
    company_id: "C004",
    company_name: "IT-A社",
    industry: "it_services",
    region: "JP",
    overall_score: 42,
    risk_level: "medium",
    category_scores: { access_control: 48, it_general: 38, financial_process: 40 },
    trend: "stable",
    open_findings: 2,
  },
  {
    company_id: "C005",
    company_name: "金融C社",
    industry: "finance",
    region: "JP",
    overall_score: 71,
    risk_level: "high",
    category_scores: { financial_process: 78, access_control: 68, it_general: 62 },
    trend: "worsening",
    open_findings: 6,
  },
];

const DEMO_BENCHMARKS: BenchmarkResult[] = [
  { industry: "finance", category: "financial_process", avg_score: 68.3, median_score: 65.0, std_dev: 12.5, sample_size: 5 },
  { industry: "finance", category: "access_control", avg_score: 58.0, median_score: 55.0, std_dev: 10.2, sample_size: 5 },
  { industry: "manufacturing", category: "inventory", avg_score: 55.0, median_score: 52.0, std_dev: 8.5, sample_size: 4 },
  { industry: "it_services", category: "it_general", avg_score: 45.0, median_score: 42.0, std_dev: 7.8, sample_size: 3 },
];

const DEMO_AUTONOMOUS_STATS: AutonomousStats = {
  total_decisions: 156,
  auto_approved: 128,
  auto_approval_rate: 0.821,
  escalated: 22,
  errors: 6,
};

const DEMO_AUTONOMOUS_DECISIONS: AutonomousDecision[] = [
  { id: "AD001", agent_type: "auditor_data_collector", action: "データ収集完了", confidence: 0.95, auto_approved: true, reason: "信頼度閾値超過", risk_level: "low", timestamp: "2025-03-15T10:30:00" },
  { id: "AD002", agent_type: "auditee_response", action: "回答生成", confidence: 0.88, auto_approved: true, reason: "定型回答パターン", risk_level: "medium", timestamp: "2025-03-15T11:00:00" },
  { id: "AD003", agent_type: "auditor_controls_tester", action: "統制テスト実行", confidence: 0.72, auto_approved: false, reason: "信頼度不足 — 人間レビュー", risk_level: "high", timestamp: "2025-03-15T11:30:00" },
];

// ── API関数 ───────────────────────────────────────

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  // TODO: 実API接続時に切り替え
  return DEMO_PORTFOLIO;
}

export async function getPortfolioCompanies(): Promise<PortfolioCompany[]> {
  return DEMO_COMPANIES;
}

export async function getBenchmarks(): Promise<BenchmarkResult[]> {
  return DEMO_BENCHMARKS;
}

export async function getAutonomousStats(): Promise<AutonomousStats> {
  return DEMO_AUTONOMOUS_STATS;
}

export async function getAutonomousDecisions(): Promise<AutonomousDecision[]> {
  return DEMO_AUTONOMOUS_DECISIONS;
}
