"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { BenchmarkResult } from "@/types/api";
import { getBenchmarks } from "@/lib/api/analytics";

export default function BenchmarkPage() {
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getBenchmarks();
        setBenchmarks(data);
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

  // 業種ごとにグループ化
  const grouped: Record<string, BenchmarkResult[]> = {};
  for (const bm of benchmarks) {
    if (!grouped[bm.industry]) grouped[bm.industry] = [];
    grouped[bm.industry].push(bm);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Industry Benchmark</h1>
        <p className="text-muted-foreground">業種別リスクベンチマーク比較</p>
      </div>

      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>対象業種数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {Object.keys(grouped).length}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>ベンチマーク項目数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{benchmarks.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>総サンプル企業数</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.max(...benchmarks.map((b) => b.sample_size), 0)}+
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Benchmarks by Industry */}
      {Object.entries(grouped).map(([industry, items]) => (
        <Card key={industry}>
          <CardHeader>
            <CardTitle className="capitalize">{industry}</CardTitle>
            <CardDescription>
              {items[0]?.sample_size || 0}社のデータに基づくベンチマーク
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {items
              .sort((a, b) => b.avg_score - a.avg_score)
              .map((bm) => (
                <div key={bm.category} className="space-y-2 rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{bm.category}</span>
                    <Badge variant="outline">n={bm.sample_size}</Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">平均: </span>
                      <span className="font-medium">{bm.avg_score}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">中央値: </span>
                      <span className="font-medium">{bm.median_score}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">標準偏差: </span>
                      <span className="font-medium">{bm.std_dev}</span>
                    </div>
                  </div>
                  <Progress value={bm.avg_score} />
                </div>
              ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
