"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  TrendingUp,
  Shield,
  AlertCircle,
  Activity,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getRiskDashboard } from "@/lib/api/controls";
import type { RiskDashboardData, RiskItem } from "@/types/api";

const riskLevelConfig: Record<
  RiskItem["risk_level"],
  { label: string; color: string; bgColor: string; variant: "danger" | "warning" | "success" | "secondary" }
> = {
  critical: { label: "Critical", color: "text-red-700", bgColor: "bg-red-100", variant: "danger" },
  high: { label: "High", color: "text-orange-700", bgColor: "bg-orange-100", variant: "warning" },
  medium: { label: "Medium", color: "text-yellow-700", bgColor: "bg-yellow-100", variant: "warning" },
  low: { label: "Low", color: "text-green-700", bgColor: "bg-green-100", variant: "success" },
};

const riskStatusConfig: Record<string, { label: string; variant: "danger" | "warning" | "success" | "secondary" }> = {
  open: { label: "Open", variant: "danger" },
  mitigated: { label: "Mitigated", variant: "success" },
  accepted: { label: "Accepted", variant: "warning" },
  closed: { label: "Closed", variant: "secondary" },
};

export default function RiskDashboardPage() {
  const [data, setData] = useState<RiskDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const dashboard = await getRiskDashboard();
        setData(dashboard);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading risk dashboard...</p>
      </div>
    );
  }

  if (!data) return null;

  const filteredRisks = statusFilter === "all"
    ? data.recent_risks
    : data.recent_risks.filter((r) => r.status === statusFilter);

  const maxCategoryCount = Math.max(...Object.values(data.by_category), 1);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Risk Dashboard</h2>
        <p className="text-muted-foreground">
          AI-detected risk monitoring and assessment
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Risks</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_risks}</div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{data.critical}</div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{data.high}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.open_risks}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mitigated</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{data.mitigated_risks}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Risk Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Score Trend</CardTitle>
            <CardDescription>7-day risk score progression</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-40">
              {data.risk_trend.map((point) => {
                const height = (point.score / 100) * 100;
                const color = point.score >= 75 ? "bg-red-400" : point.score >= 60 ? "bg-yellow-400" : "bg-green-400";
                return (
                  <div
                    key={point.date}
                    className="flex-1 flex flex-col items-center gap-1"
                  >
                    <span className="text-xs font-medium">{point.score}</span>
                    <div
                      className={`w-full rounded-t ${color} transition-all duration-300`}
                      style={{ height: `${height}%` }}
                      title={`${point.date}: Score ${point.score}, ${point.count} risks`}
                    />
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(point.date).toLocaleDateString("en", { month: "short", day: "numeric" })}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Risk by Category */}
        <Card>
          <CardHeader>
            <CardTitle>Risks by Category</CardTitle>
            <CardDescription>Distribution of detected risks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(data.by_category).map(([category, count]) => (
                <div key={category} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{category}</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{ width: `${(count / maxCategoryCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risk Items */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Risk Registry</CardTitle>
              <CardDescription>All detected risks and their status</CardDescription>
            </div>
            <select
              className="rounded-md border px-3 py-1.5 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="mitigated">Mitigated</option>
              <option value="accepted">Accepted</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredRisks.map((risk) => {
              const level = riskLevelConfig[risk.risk_level];
              const status = riskStatusConfig[risk.status];
              return (
                <div
                  key={risk.id}
                  className={`rounded-md border p-4 border-l-4 ${
                    risk.risk_level === "critical"
                      ? "border-l-red-500"
                      : risk.risk_level === "high"
                        ? "border-l-orange-500"
                        : risk.risk_level === "medium"
                          ? "border-l-yellow-500"
                          : "border-l-green-500"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{risk.title}</span>
                        <Badge variant={level.variant}>{level.label}</Badge>
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {risk.description}
                      </p>
                      <div className="flex items-center gap-4 pt-1 text-xs text-muted-foreground">
                        <span>Category: {risk.category}</span>
                        <span>Source: {risk.source}</span>
                        <span>
                          Detected: {new Date(risk.detected_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4 text-right">
                      <div className="text-2xl font-bold">{risk.risk_score}</div>
                      <div className="text-xs text-muted-foreground">Risk Score</div>
                    </div>
                  </div>
                </div>
              );
            })}
            {filteredRisks.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">
                No risks match the selected filter
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
