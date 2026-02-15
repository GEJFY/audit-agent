"use client";

import { useEffect, useState, useCallback } from "react";
import { ShieldCheck, AlertTriangle, Clock, CheckCircle2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { getControlScorecard } from "@/lib/api/controls";
import type { ControlScorecard, ControlScore } from "@/types/api";

const statusConfig: Record<
  ControlScore["status"],
  { label: string; color: string; variant: "success" | "warning" | "danger" | "secondary" }
> = {
  effective: { label: "Effective", color: "bg-green-500", variant: "success" },
  partially_effective: { label: "Partial", color: "bg-yellow-500", variant: "warning" },
  ineffective: { label: "Ineffective", color: "bg-red-500", variant: "danger" },
  not_tested: { label: "Not Tested", color: "bg-gray-400", variant: "secondary" },
};

const remediationConfig: Record<string, { label: string; variant: "success" | "warning" | "danger" | "secondary" }> = {
  none: { label: "None", variant: "secondary" },
  in_progress: { label: "In Progress", variant: "warning" },
  completed: { label: "Completed", variant: "success" },
  overdue: { label: "Overdue", variant: "danger" },
};

function scoreColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

export default function ControlsPage() {
  const [scorecard, setScorecard] = useState<ControlScorecard | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getControlScorecard();
        setScorecard(data);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filteredControls = useCallback(() => {
    if (!scorecard) return [];
    return scorecard.controls.filter((c) => {
      if (filterCategory !== "all" && c.category !== filterCategory) return false;
      if (filterStatus !== "all" && c.status !== filterStatus) return false;
      return true;
    });
  }, [scorecard, filterCategory, filterStatus]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading controls scorecard...</p>
      </div>
    );
  }

  if (!scorecard) return null;

  const categories = Object.keys(scorecard.by_category);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Controls Scorecard</h2>
        <p className="text-muted-foreground">
          Internal control effectiveness assessment
        </p>
      </div>

      {/* Overall Score */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="md:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Overall Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="relative flex h-20 w-20 items-center justify-center">
                <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke={scorecard.overall_score >= 80 ? "#22c55e" : scorecard.overall_score >= 60 ? "#eab308" : "#ef4444"}
                    strokeWidth="3"
                    strokeDasharray={`${scorecard.overall_score}, 100`}
                  />
                </svg>
                <span className="absolute text-xl font-bold">
                  {scorecard.overall_score}
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                <p>{scorecard.total_controls} controls assessed</p>
                <p>{scorecard.effective + scorecard.partially_effective} operational</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Effective</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{scorecard.effective}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Partial</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{scorecard.partially_effective}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ineffective</CardTitle>
            <ShieldCheck className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{scorecard.ineffective}</div>
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Score by Category</CardTitle>
          <CardDescription>Control effectiveness by domain</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {categories.map((cat) => {
              const data = scorecard.by_category[cat];
              return (
                <div key={cat} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{cat}</span>
                    <span className="text-muted-foreground">
                      {data.score}% ({data.count} controls)
                    </span>
                  </div>
                  <Progress
                    value={data.score}
                    indicatorClassName={scoreColor(data.score)}
                  />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Controls Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Control Details</CardTitle>
              <CardDescription>Individual control test results</CardDescription>
            </div>
            <div className="flex gap-2">
              <select
                className="rounded-md border px-3 py-1.5 text-sm"
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="all">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <select
                className="rounded-md border px-3 py-1.5 text-sm"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">All Status</option>
                <option value="effective">Effective</option>
                <option value="partially_effective">Partial</option>
                <option value="ineffective">Ineffective</option>
                <option value="not_tested">Not Tested</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredControls().map((control) => {
              const status = statusConfig[control.status];
              const remediation = remediationConfig[control.remediation_status];
              return (
                <div
                  key={control.id}
                  className="flex items-center justify-between rounded-md border p-4"
                >
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">
                        {control.control_id}
                      </span>
                      <span className="font-medium text-sm">{control.control_name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{control.description}</p>
                    <div className="flex items-center gap-2 pt-1">
                      <Badge variant={status.variant}>{status.label}</Badge>
                      {control.findings_count > 0 && (
                        <Badge variant="outline">
                          {control.findings_count} finding{control.findings_count > 1 ? "s" : ""}
                        </Badge>
                      )}
                      {control.remediation_status !== "none" && (
                        <Badge variant={remediation.variant}>{remediation.label}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 ml-4">
                    <div className="text-right">
                      <div className="text-2xl font-bold">
                        {control.status === "not_tested" ? "-" : control.score}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {control.last_tested
                          ? `Tested ${new Date(control.last_tested).toLocaleDateString()}`
                          : "Not tested"}
                      </div>
                    </div>
                    {control.status !== "not_tested" && (
                      <div className="w-16">
                        <Progress
                          value={control.score}
                          indicatorClassName={scoreColor(control.score)}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {filteredControls().length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">
                No controls match the selected filters
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
