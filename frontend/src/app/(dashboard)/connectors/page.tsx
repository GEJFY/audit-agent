"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Plug,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  Clock,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  getConnectorsHealth,
  getConnectorsMetrics,
} from "@/lib/api/connectors";
import type {
  ConnectorsHealthResponse,
  ConnectorHealth,
  ConnectorsMetricsResponse,
} from "@/lib/api/connectors";

const statusConfig: Record<
  ConnectorHealth["status"],
  {
    label: string;
    icon: typeof CheckCircle2;
    variant: "success" | "warning" | "danger" | "secondary";
  }
> = {
  healthy: { label: "Healthy", icon: CheckCircle2, variant: "success" },
  unhealthy: { label: "Unhealthy", icon: AlertTriangle, variant: "warning" },
  error: { label: "Error", icon: XCircle, variant: "danger" },
  unknown: { label: "Unknown", icon: Clock, variant: "secondary" },
};

const overallConfig: Record<
  string,
  { label: string; color: string }
> = {
  healthy: { label: "All Systems Operational", color: "text-green-600" },
  degraded: { label: "Degraded Performance", color: "text-yellow-600" },
  unhealthy: { label: "System Outage", color: "text-red-600" },
};

export default function ConnectorsPage() {
  const [health, setHealth] = useState<ConnectorsHealthResponse | null>(null);
  const [metrics, setMetrics] = useState<ConnectorsMetricsResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [healthData, metricsData] = await Promise.all([
        getConnectorsHealth(),
        getConnectorsMetrics(),
      ]);
      setHealth(healthData);
      setMetrics(metricsData);
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Failed to fetch connector data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // 30秒ごとに自動リフレッシュ
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Connector Health
          </h1>
          <p className="text-muted-foreground">
            外部コネクタの接続状態とサーキットブレーカーの監視
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastRefresh && (
            <p className="text-xs text-muted-foreground">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      {health && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Plug className="h-5 w-5" />
                Overall Status
              </CardTitle>
              <span
                className={`text-lg font-semibold ${overallConfig[health.status]?.color || ""}`}
              >
                {overallConfig[health.status]?.label || health.status}
              </span>
            </div>
            <CardDescription>
              {health.healthy}/{health.total} connectors operational
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress
              value={(health.healthy / health.total) * 100}
              className="h-2"
            />
          </CardContent>
        </Card>
      )}

      {/* Connector Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {health?.connectors.map((connector) => {
          const config = statusConfig[connector.status];
          const StatusIcon = config.icon;
          const connectorMetrics =
            metrics?.connectors[connector.name];

          return (
            <Card key={connector.name}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Plug className="h-4 w-4" />
                    {connector.name.toUpperCase()}
                  </CardTitle>
                  <Badge variant={config.variant}>
                    <StatusIcon className="mr-1 h-3 w-3" />
                    {config.label}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Latency */}
                {connector.latency_ms !== undefined && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      Latency
                    </span>
                    <span className="font-mono">
                      {connector.latency_ms.toFixed(1)}ms
                    </span>
                  </div>
                )}

                {/* Circuit Breaker */}
                {connector.circuit_breaker && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Zap className="h-3 w-3" />
                        Circuit Breaker
                      </span>
                      <Badge
                        variant={
                          connector.circuit_breaker.state === "open"
                            ? "danger"
                            : "success"
                        }
                      >
                        {connector.circuit_breaker.state.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        Failures
                      </span>
                      <span className="font-mono">
                        {connector.circuit_breaker.failure_count}/
                        {connector.circuit_breaker.failure_threshold}
                      </span>
                    </div>
                    <Progress
                      value={
                        (connector.circuit_breaker.failure_count /
                          connector.circuit_breaker.failure_threshold) *
                        100
                      }
                      className="h-1.5"
                    />
                  </div>
                )}

                {/* Cooldown (from metrics) */}
                {connectorMetrics?.circuit_breaker && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      Cooldown
                    </span>
                    <span className="font-mono">
                      {connectorMetrics.circuit_breaker.cooldown_seconds}s
                    </span>
                  </div>
                )}

                {/* Error message */}
                {connector.error && (
                  <div className="rounded-md bg-destructive/10 p-2 text-xs text-destructive">
                    {connector.error}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Loading state */}
      {loading && !health && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="mr-2 h-5 w-5 animate-spin text-muted-foreground" />
          <span className="text-muted-foreground">
            Loading connector status...
          </span>
        </div>
      )}
    </div>
  );
}
