"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
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
import type { PortfolioSummary, PortfolioCompany } from "@/types/api";
import {
  getPortfolioSummary,
  getPortfolioCompanies,
} from "@/lib/api/analytics";

const riskLevelColors: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-green-500",
};

const riskLevelLabels: Record<string, string> = {
  critical: "クリティカル",
  high: "高",
  medium: "中",
  low: "低",
};

const trendIcons: Record<string, typeof TrendingUp> = {
  worsening: TrendingDown,
  stable: Minus,
  improving: TrendingUp,
};

export default function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [companies, setCompanies] = useState<PortfolioCompany[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryData, companiesData] = await Promise.all([
          getPortfolioSummary(),
          getPortfolioCompanies(),
        ]);
        setSummary(summaryData);
        setCompanies(companiesData);
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

  if (!summary) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Portfolio Overview</h1>
        <p className="text-muted-foreground">
          {summary.total_companies}社のリスクポートフォリオ
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>管理企業数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {summary.total_companies}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>平均リスクスコア</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.avg_overall_score}
            </div>
            <Progress value={summary.avg_overall_score} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>クリティカル企業</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold text-red-500">
                {summary.risk_distribution.critical || 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>アラート数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.alerts_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts */}
      {summary.alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>アラート</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary.alerts.map((alert, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg border p-3"
              >
                <AlertTriangle
                  className={`mt-0.5 h-4 w-4 ${
                    alert.severity === "critical"
                      ? "text-red-500"
                      : "text-orange-500"
                  }`}
                />
                <div>
                  <p className="text-sm font-medium">{alert.description}</p>
                  <p className="text-xs text-muted-foreground">
                    影響企業: {alert.affected_companies.length}社
                  </p>
                </div>
                <Badge
                  variant={
                    alert.severity === "critical" ? "destructive" : "secondary"
                  }
                  className="ml-auto"
                >
                  {alert.severity}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Risk Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>リスクレベル分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-6">
            {Object.entries(summary.risk_distribution).map(([level, count]) => (
              <div key={level} className="flex items-center gap-2">
                <div
                  className={`h-3 w-3 rounded-full ${riskLevelColors[level]}`}
                />
                <span className="text-sm text-muted-foreground">
                  {riskLevelLabels[level] || level}
                </span>
                <span className="font-bold">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Companies Table */}
      <Card>
        <CardHeader>
          <CardTitle>企業一覧</CardTitle>
          <CardDescription>リスクスコア降順</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {companies
              .sort((a, b) => b.overall_score - a.overall_score)
              .map((company) => {
                const TrendIcon =
                  trendIcons[company.trend] || Minus;
                return (
                  <div
                    key={company.company_id}
                    className="flex items-center gap-4 rounded-lg border p-3"
                  >
                    <div
                      className={`h-2 w-2 rounded-full ${riskLevelColors[company.risk_level]}`}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {company.company_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {company.industry} / {company.region}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold">
                        {company.overall_score}
                      </p>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <TrendIcon className="h-3 w-3" />
                        {company.trend}
                      </div>
                    </div>
                    <Badge variant="outline">
                      所見 {company.open_findings}
                    </Badge>
                  </div>
                );
              })}
          </div>
        </CardContent>
      </Card>

      {/* Category Averages */}
      <Card>
        <CardHeader>
          <CardTitle>カテゴリ別平均スコア</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(summary.category_averages)
            .sort(([, a], [, b]) => b - a)
            .map(([category, avg]) => (
              <div key={category} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{category}</span>
                  <span className="font-medium">{avg}</span>
                </div>
                <Progress value={avg} />
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}
