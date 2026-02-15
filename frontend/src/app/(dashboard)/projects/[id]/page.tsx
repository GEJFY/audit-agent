"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getProject, deleteProject } from "@/lib/api/projects";
import type { AuditProject } from "@/types/api";

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

const phaseSteps = ["draft", "planning", "fieldwork", "reporting", "completed"];

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<AuditProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const data = await getProject(projectId);
        setProject(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load project");
      } finally {
        setLoading(false);
      }
    };
    fetchProject();
  }, [projectId]);

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      await deleteProject(projectId);
      router.push("/projects");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.push("/projects")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Projects
        </Button>
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            {error || "Project not found"}
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentPhaseIndex = phaseSteps.indexOf(project.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push("/projects")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              {project.name}
            </h2>
            <p className="text-muted-foreground">{project.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              statusColor[project.status] || "bg-gray-100"
            }`}
          >
            {statusLabel[project.status] || project.status}
          </span>
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="mr-1 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Phase Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Audit Phase Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            {phaseSteps.map((step, index) => (
              <div key={step} className="flex flex-1 items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium ${
                      index <= currentPhaseIndex
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {index + 1}
                  </div>
                  <span className="mt-1 text-xs capitalize">{step}</span>
                </div>
                {index < phaseSteps.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 flex-1 ${
                      index < currentPhaseIndex ? "bg-primary" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Project Details */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Department</span>
              <span>{project.department}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Fiscal Year</span>
              <span>FY{project.fiscal_year}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Created</span>
              <span>
                {new Date(project.created_at).toLocaleDateString("ja-JP")}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Last Updated</span>
              <span>
                {new Date(project.updated_at).toLocaleDateString("ja-JP")}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Findings</CardTitle>
            <CardDescription>
              Audit findings for this project
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No findings yet. Start fieldwork to detect issues.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
