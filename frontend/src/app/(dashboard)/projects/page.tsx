"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getProjects } from "@/lib/api/projects";
import type { AuditProject } from "@/types/api";
import { CreateProjectDialog } from "@/components/create-project-dialog";

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

export default function ProjectsPage() {
  const [projects, setProjects] = useState<AuditProject[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getProjects({
        status: statusFilter || undefined,
        limit: 50,
      });
      setProjects(data.projects);
      setTotal(data.total);
    } catch {
      // API未接続時は空表示
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Projects</h2>
          <p className="text-muted-foreground">
            Manage audit projects ({total} total)
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2">
        {["", "draft", "planning", "fieldwork", "reporting", "completed"].map(
          (status) => (
            <Button
              key={status}
              variant={statusFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(status)}
            >
              {status === "" ? "All" : statusLabel[status] || status}
            </Button>
          ),
        )}
      </div>

      {/* Project Cards */}
      {loading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : projects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="mb-4 text-muted-foreground">
              No projects found
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create First Project
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-medium ${
                        statusColor[project.status] || "bg-gray-100"
                      }`}
                    >
                      {statusLabel[project.status] || project.status}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
                    {project.description || "No description"}
                  </p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{project.department}</span>
                    <span>FY{project.fiscal_year}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreateProjectDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={fetchProjects}
      />
    </div>
  );
}
