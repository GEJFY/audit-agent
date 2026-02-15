"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FolderKanban,
  CheckCircle,
  Bot,
  AlertTriangle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth-store";
import {
  getDashboardStats,
  getProjects,
  type DashboardStats,
} from "@/lib/api/projects";
import type { AuditProject } from "@/types/api";

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [stats, setStats] = useState<DashboardStats>({
    activeProjects: 0,
    pendingApprovals: 0,
    agentDecisions: 0,
    riskAlerts: 0,
  });
  const [recentProjects, setRecentProjects] = useState<AuditProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, projectsData] = await Promise.allSettled([
          getDashboardStats(),
          getProjects({ limit: 5 }),
        ]);
        if (statsData.status === "fulfilled") setStats(statsData.value);
        if (projectsData.status === "fulfilled")
          setRecentProjects(projectsData.value.projects);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const statCards = [
    {
      title: "Active Projects",
      value: stats.activeProjects,
      icon: FolderKanban,
      href: "/projects",
    },
    {
      title: "Pending Approvals",
      value: stats.pendingApprovals,
      icon: CheckCircle,
      href: "/approvals",
    },
    {
      title: "Agent Decisions",
      value: stats.agentDecisions,
      icon: Bot,
      href: "/agents",
    },
    {
      title: "Risk Alerts",
      value: stats.riskAlerts,
      icon: AlertTriangle,
      href: "/dashboard",
    },
  ];

  const statusLabel: Record<string, string> = {
    draft: "Draft",
    planning: "Planning",
    fieldwork: "Fieldwork",
    reporting: "Reporting",
    completed: "Completed",
  };

  const statusColor: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    planning: "bg-blue-100 text-blue-700",
    fieldwork: "bg-yellow-100 text-yellow-700",
    reporting: "bg-purple-100 text-purple-700",
    completed: "bg-green-100 text-green-700",
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          {user?.full_name || "User"} - AI Internal Audit Overview
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Link key={card.title} href={card.href}>
            <Card className="transition-shadow hover:shadow-md">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {card.title}
                </CardTitle>
                <card.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? "-" : card.value}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>Latest audit projects</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : recentProjects.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No projects yet.{" "}
                <Link
                  href="/projects"
                  className="text-primary hover:underline"
                >
                  Create one
                </Link>
              </p>
            ) : (
              <div className="space-y-3">
                {recentProjects.map((project) => (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="flex items-center justify-between rounded-md border p-3 transition-colors hover:bg-muted/50"
                  >
                    <div>
                      <p className="text-sm font-medium">{project.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {project.department}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-medium ${
                        statusColor[project.status] || "bg-gray-100"
                      }`}
                    >
                      {statusLabel[project.status] || project.status}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Agent Status</CardTitle>
            <CardDescription>
              Current state of AI audit agents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                "Auditor Orchestrator",
                "Planner",
                "Controls Tester",
                "Anomaly Detective",
                "Report Writer",
                "Knowledge Agent",
              ].map((name) => (
                <div
                  key={name}
                  className="flex items-center justify-between text-sm"
                >
                  <span>{name}</span>
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                    Ready
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
