"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FileText,
  Search,
  CheckCircle,
  XCircle,
  Clock,
  Download,
  Trash2,
  ExternalLink,
  Filter,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import { formatFileSize } from "@/lib/api/evidence";
import type { EvidenceItem, BoxSearchResult } from "@/types/api";

const statusConfig: Record<
  string,
  { icon: typeof Clock; label: string; color: string }
> = {
  pending: { icon: Clock, label: "Pending", color: "text-yellow-500" },
  verified: { icon: CheckCircle, label: "Verified", color: "text-green-500" },
  rejected: { icon: XCircle, label: "Rejected", color: "text-red-500" },
};

const sourceLabels: Record<string, string> = {
  upload: "Upload",
  box: "Box",
  sharepoint: "SharePoint",
  manual: "Manual",
};

type TabType = "evidence" | "box-search";

export default function EvidencePage() {
  const [activeTab, setActiveTab] = useState<TabType>("evidence");
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [boxResults, setBoxResults] = useState<BoxSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [boxSearchQuery, setBoxSearchQuery] = useState("");
  const [boxSearching, setBoxSearching] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchEvidence = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (statusFilter !== "all") params.status = statusFilter;
      const query = new URLSearchParams(params).toString();
      const path = `/api/v1/evidence${query ? `?${query}` : ""}`;
      const data = await apiClient.get<EvidenceItem[]>(path);
      setEvidenceList(data);
    } catch {
      // API未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchEvidence();
  }, [fetchEvidence]);

  const handleStatusUpdate = async (
    id: string,
    status: "verified" | "rejected",
  ) => {
    setActionLoading(id);
    try {
      await apiClient.put(`/api/v1/evidence/${id}/status`, { status });
      setEvidenceList((prev) =>
        prev.map((item) => (item.id === id ? { ...item, status } : item)),
      );
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    setActionLoading(id);
    try {
      await apiClient.delete(`/api/v1/evidence/${id}`);
      setEvidenceList((prev) => prev.filter((item) => item.id !== id));
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const handleBoxSearch = async () => {
    if (!boxSearchQuery.trim()) return;
    setBoxSearching(true);
    try {
      const data = await apiClient.post<BoxSearchResult[]>(
        "/api/v1/connectors/box/search",
        { query: boxSearchQuery },
      );
      setBoxResults(data);
    } catch {
      setBoxResults([]);
    } finally {
      setBoxSearching(false);
    }
  };

  const handleBoxImport = async (fileId: string) => {
    setActionLoading(fileId);
    try {
      await apiClient.post("/api/v1/connectors/box/import", {
        file_id: fileId,
      });
      setBoxResults((prev) => prev.filter((r) => r.id !== fileId));
    } catch {
      // エラーハンドリング
    } finally {
      setActionLoading(null);
    }
  };

  const filteredEvidence = evidenceList.filter(
    (item) =>
      !searchQuery ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const stats = {
    total: evidenceList.length,
    verified: evidenceList.filter((e) => e.status === "verified").length,
    pending: evidenceList.filter((e) => e.status === "pending").length,
    rejected: evidenceList.filter((e) => e.status === "rejected").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Evidence</h2>
        <p className="text-muted-foreground">
          Manage audit evidence and connect external sources
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Verified</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.verified}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pending}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rejected</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.rejected}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "evidence"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("evidence")}
        >
          Evidence List
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "box-search"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("box-search")}
        >
          Box Search
        </button>
      </div>

      {/* Evidence List Tab */}
      {activeTab === "evidence" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search evidence..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              {["all", "pending", "verified", "rejected"].map((status) => (
                <Button
                  key={status}
                  variant={statusFilter === status ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                >
                  {status === "all" ? "All" : status.charAt(0).toUpperCase() + status.slice(1)}
                </Button>
              ))}
            </div>
          </div>

          {/* Evidence Cards */}
          {loading ? (
            <div className="text-center text-muted-foreground py-8">
              Loading...
            </div>
          ) : filteredEvidence.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="text-lg font-medium">No evidence found</p>
                <p className="text-sm text-muted-foreground">
                  Upload files or search Box to add evidence
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredEvidence.map((item) => {
                const statusInfo = statusConfig[item.status] || statusConfig.pending;
                const StatusIcon = statusInfo.icon;
                return (
                  <Card key={item.id}>
                    <CardContent className="flex items-center gap-4 py-4">
                      {/* File icon */}
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <FileText className="h-5 w-5 text-primary" />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium truncate">{item.name}</p>
                          <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs">
                            {sourceLabels[item.source] || item.source}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground truncate">
                          {item.description || "No description"}
                        </p>
                        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{formatFileSize(item.file_size)}</span>
                          <span>{item.type}</span>
                          <span>
                            {new Date(item.created_at).toLocaleDateString("ja-JP")}
                          </span>
                          {item.tags.length > 0 && (
                            <span className="flex gap-1">
                              {item.tags.map((tag) => (
                                <span
                                  key={tag}
                                  className="rounded bg-muted px-1.5 py-0.5"
                                >
                                  {tag}
                                </span>
                              ))}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Status */}
                      <div className={`flex items-center gap-1 text-sm ${statusInfo.color}`}>
                        <StatusIcon className="h-4 w-4" />
                        <span>{statusInfo.label}</span>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-1">
                        {item.status === "pending" && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Verify"
                              onClick={() => handleStatusUpdate(item.id, "verified")}
                              disabled={actionLoading === item.id}
                            >
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Reject"
                              onClick={() => handleStatusUpdate(item.id, "rejected")}
                              disabled={actionLoading === item.id}
                            >
                              <XCircle className="h-4 w-4 text-red-500" />
                            </Button>
                          </>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Delete"
                          onClick={() => handleDelete(item.id)}
                          disabled={actionLoading === item.id}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Box Search Tab */}
      {activeTab === "box-search" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Search Box</CardTitle>
              <CardDescription>
                Search files in Box and import as audit evidence
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search Box files..."
                    className="pl-10"
                    value={boxSearchQuery}
                    onChange={(e) => setBoxSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleBoxSearch();
                    }}
                  />
                </div>
                <Button onClick={handleBoxSearch} disabled={boxSearching}>
                  {boxSearching ? "Searching..." : "Search"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Box Search Results */}
          {boxResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {boxResults.length} results found
              </p>
              {boxResults.map((result) => (
                <Card key={result.id}>
                  <CardContent className="flex items-center gap-4 py-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
                      <ExternalLink className="h-5 w-5 text-blue-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{result.name}</p>
                      <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{formatFileSize(result.size)}</span>
                        {result.parent_folder && (
                          <span>in {result.parent_folder}</span>
                        )}
                        <span>
                          {new Date(result.modified_at).toLocaleDateString("ja-JP")}
                        </span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleBoxImport(result.id)}
                      disabled={actionLoading === result.id}
                    >
                      <Download className="mr-1 h-4 w-4" />
                      Import
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
