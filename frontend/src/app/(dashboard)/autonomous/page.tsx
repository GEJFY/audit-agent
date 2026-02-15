"use client";

import { useEffect, useState } from "react";
import { Cpu, CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { AutonomousStats, AutonomousDecision } from "@/types/api";
import {
  getAutonomousStats,
  getAutonomousDecisions,
} from "@/lib/api/analytics";

export default function AutonomousPage() {
  const [stats, setStats] = useState<AutonomousStats | null>(null);
  const [decisions, setDecisions] = useState<AutonomousDecision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, decisionsData] = await Promise.all([
          getAutonomousStats(),
          getAutonomousDecisions(),
        ]);
        setStats(statsData);
        setDecisions(decisionsData);
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

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Autonomous Mode Monitor</h1>
        <p className="text-muted-foreground">
          自律実行モードの判断履歴と統計
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>総判断数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {stats.total_decisions}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>自動承認率</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(stats.auto_approval_rate * 100).toFixed(1)}%
            </div>
            <Progress
              value={stats.auto_approval_rate * 100}
              className="mt-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>エスカレーション</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              <span className="text-2xl font-bold">{stats.escalated}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>エラー</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              <span className="text-2xl font-bold">{stats.errors}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Approval Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>判断内訳</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-green-50 p-4 text-center dark:bg-green-950">
              <CheckCircle className="mx-auto h-8 w-8 text-green-500" />
              <p className="mt-2 text-2xl font-bold">{stats.auto_approved}</p>
              <p className="text-sm text-muted-foreground">自動承認</p>
            </div>
            <div className="rounded-lg bg-orange-50 p-4 text-center dark:bg-orange-950">
              <AlertTriangle className="mx-auto h-8 w-8 text-orange-500" />
              <p className="mt-2 text-2xl font-bold">{stats.escalated}</p>
              <p className="text-sm text-muted-foreground">エスカレーション</p>
            </div>
            <div className="rounded-lg bg-red-50 p-4 text-center dark:bg-red-950">
              <XCircle className="mx-auto h-8 w-8 text-red-500" />
              <p className="mt-2 text-2xl font-bold">{stats.errors}</p>
              <p className="text-sm text-muted-foreground">エラー</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Decisions */}
      <Card>
        <CardHeader>
          <CardTitle>最近の判断履歴</CardTitle>
          <CardDescription>Autonomousモードの自動判断ログ</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {decisions.map((decision) => (
              <div
                key={decision.id}
                className="flex items-center gap-4 rounded-lg border p-3"
              >
                {decision.auto_approved ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium">{decision.action}</p>
                  <p className="text-xs text-muted-foreground">
                    {decision.agent_type} / {decision.reason}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">
                    {(decision.confidence * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(decision.timestamp).toLocaleString("ja-JP")}
                  </p>
                </div>
                <Badge
                  variant={
                    decision.risk_level === "low"
                      ? "secondary"
                      : decision.risk_level === "high"
                        ? "destructive"
                        : "outline"
                  }
                >
                  {decision.risk_level}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
