"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { RiskForecast } from "@/types/api";
import { getRiskForecast } from "@/lib/api/reports";

const trendConfig: Record<
  string,
  { label: string; icon: typeof TrendingUp; color: string }
> = {
  improving: { label: "改善傾向", icon: TrendingUp, color: "text-green-500" },
  stable: { label: "安定", icon: Minus, color: "text-gray-500" },
  worsening: {
    label: "悪化傾向",
    icon: TrendingDown,
    color: "text-red-500",
  },
};

export default function ForecastPage() {
  const [forecast, setForecast] = useState<RiskForecast | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getRiskForecast();
        setForecast(data);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-muted-foreground">読み込み中...</p>
      </div>
    );
  }

  if (!forecast) return null;

  const trend = trendConfig[forecast.risk_trend] || trendConfig.stable;
  const TrendIcon = trend.icon;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Risk Forecast</h1>
        <p className="text-muted-foreground">3ヶ月先リスク予測ダッシュボード</p>
      </div>

      {/* Current vs Predicted */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>現在のリスクスコア</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{forecast.current_score}</div>
            <Progress value={forecast.current_score} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>リスクトレンド</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`flex items-center gap-2 ${trend.color}`}>
              <TrendIcon className="h-6 w-6" />
              <span className="text-xl font-bold">{trend.label}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>予測信頼度</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {(forecast.confidence * 100).toFixed(0)}%
            </div>
            <Progress value={forecast.confidence * 100} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Predicted Scores Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>月別予測スコア</CardTitle>
          <CardDescription>今後3ヶ月の予測リスクスコア推移</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Current baseline */}
            <div className="flex items-center gap-4">
              <span className="w-24 text-sm text-muted-foreground">現在</span>
              <div className="flex-1">
                <Progress value={forecast.current_score} />
              </div>
              <span className="w-12 text-right text-sm font-bold">
                {forecast.current_score}
              </span>
            </div>

            {/* Predictions */}
            {forecast.predicted_scores.map((point) => {
              const diff = point.score - forecast.current_score;
              return (
                <div key={point.month} className="flex items-center gap-4">
                  <span className="w-24 text-sm text-muted-foreground">
                    {point.month}
                  </span>
                  <div className="flex-1">
                    <Progress value={point.score} />
                  </div>
                  <span className="w-12 text-right text-sm font-bold">
                    {point.score}
                  </span>
                  <span
                    className={`w-12 text-right text-xs ${
                      diff > 0 ? "text-red-500" : "text-green-500"
                    }`}
                  >
                    {diff > 0 ? "+" : ""}
                    {diff.toFixed(1)}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Category Forecasts */}
      <Card>
        <CardHeader>
          <CardTitle>カテゴリ別リスク予測</CardTitle>
          <CardDescription>現在 → 予測（3ヶ月後）</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.entries(forecast.category_forecasts)
            .sort(([, a], [, b]) => b.predicted - a.predicted)
            .map(([category, data]) => {
              const diff = data.predicted - data.current;
              const isIncreasing = diff > 0;
              return (
                <div key={category} className="space-y-2 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{category}</span>
                    <div className="flex items-center gap-2">
                      {isIncreasing ? (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      ) : (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      )}
                      <Badge
                        variant={isIncreasing ? "destructive" : "secondary"}
                      >
                        {diff > 0 ? "+" : ""}
                        {diff.toFixed(1)}
                      </Badge>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">現在: </span>
                      <span className="font-medium">{data.current}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">予測: </span>
                      <span className="font-medium">{data.predicted}</span>
                    </div>
                  </div>
                  <Progress value={data.predicted} />
                </div>
              );
            })}
        </CardContent>
      </Card>
    </div>
  );
}
