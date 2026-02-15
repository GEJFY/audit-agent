/** Reports API クライアント — リスクインテリジェンスレポート */

import type { RiskForecast } from "@/types/api";

// ── デモデータ ────────────────────────────────────
const DEMO_FORECAST: RiskForecast = {
  current_score: 62.0,
  predicted_scores: [
    { month: "2025-04", score: 64.5 },
    { month: "2025-05", score: 67.2 },
    { month: "2025-06", score: 65.8 },
  ],
  confidence: 0.78,
  risk_trend: "worsening",
  category_forecasts: {
    financial_process: { current: 72.0, predicted: 78.0 },
    access_control: { current: 55.0, predicted: 58.5 },
    it_general: { current: 48.0, predicted: 46.0 },
    inventory: { current: 40.0, predicted: 42.0 },
  },
};

// ── API関数 ───────────────────────────────────────

export async function getRiskForecast(): Promise<RiskForecast> {
  // TODO: 実API接続時に切り替え
  return DEMO_FORECAST;
}
