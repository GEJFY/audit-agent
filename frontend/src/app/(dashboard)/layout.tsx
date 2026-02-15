"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/sidebar";
import { useAuthStore } from "@/stores/auth-store";
import { getCurrentUser } from "@/lib/api/auth";
import { apiClient } from "@/lib/api/client";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, isLoading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    const checkAuth = async () => {
      const token = apiClient.getAccessToken();
      if (!token) {
        setUser(null);
        router.push("/login");
        return;
      }

      try {
        const user = await getCurrentUser();
        setUser(user);
      } catch {
        setUser(null);
        router.push("/login");
      }
    };

    checkAuth();
  }, [router, setUser, setLoading]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-muted/30 p-6">
        {children}
      </main>
    </div>
  );
}
