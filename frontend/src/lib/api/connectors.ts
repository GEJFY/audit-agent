/** コネクタヘルスチェック・メトリクス API */

import { apiClient } from "./client";

export interface ConnectorHealth {
  name: string;
  status: "healthy" | "unhealthy" | "error" | "unknown";
  latency_ms?: number;
  error?: string;
  circuit_breaker?: {
    state: "open" | "closed" | "unknown";
    failure_count: number;
    failure_threshold: number;
  };
}

export interface ConnectorsHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  total: number;
  healthy: number;
  connectors: ConnectorHealth[];
}

export interface ConnectorMetrics {
  circuit_breaker?: {
    state: "open" | "closed";
    failure_count: number;
    failure_threshold: number;
    cooldown_seconds: number;
  };
  error?: string;
}

export interface ConnectorsMetricsResponse {
  connectors: Record<string, ConnectorMetrics>;
}

/** 全コネクタのヘルスチェック */
export async function getConnectorsHealth(): Promise<ConnectorsHealthResponse> {
  return apiClient.get<ConnectorsHealthResponse>(
    "/api/v1/connectors/health",
  );
}

/** 個別コネクタのヘルスチェック */
export async function getConnectorHealth(
  name: string,
): Promise<ConnectorHealth> {
  return apiClient.get<ConnectorHealth>(
    `/api/v1/connectors/${name}/health`,
  );
}

/** 全コネクタのメトリクス */
export async function getConnectorsMetrics(): Promise<ConnectorsMetricsResponse> {
  return apiClient.get<ConnectorsMetricsResponse>(
    "/api/v1/connectors/metrics",
  );
}
