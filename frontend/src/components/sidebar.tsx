"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  MessageSquare,
  CheckCircle,
  FileText,
  Bot,
  ShieldCheck,
  AlertTriangle,
  LogOut,
  Building2,
  TrendingUp,
  BarChart3,
  Cpu,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { logout } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", href: "/projects", icon: FolderKanban },
  { name: "Controls", href: "/controls", icon: ShieldCheck },
  { name: "Risk", href: "/risk", icon: AlertTriangle },
  { name: "Dialogue", href: "/dialogue", icon: MessageSquare },
  { name: "Approvals", href: "/approvals", icon: CheckCircle },
  { name: "Evidence", href: "/evidence", icon: FileText },
  { name: "Agents", href: "/agents", icon: Bot },
];

const executiveNavigation = [
  { name: "Portfolio", href: "/portfolio", icon: Building2 },
  { name: "Forecast", href: "/forecast", icon: TrendingUp },
  { name: "Benchmark", href: "/benchmark", icon: BarChart3 },
  { name: "Autonomous", href: "/autonomous", icon: Cpu },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const logoutStore = useAuthStore((state) => state.logout);

  const handleLogout = async () => {
    await logout();
    logoutStore();
    window.location.href = "/login";
  };

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-lg font-bold text-primary">Audit Agent</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}

        {/* Executive Section */}
        <div className="mt-4 border-t pt-4">
          <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Executive
          </p>
          {executiveNavigation.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* User info */}
      <div className="border-t p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
            {user?.full_name?.charAt(0) || "U"}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="truncate text-sm font-medium">
              {user?.full_name || "User"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {user?.role || ""}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
