import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactElement } from "react";

import { api } from "./api";
import { AppShell } from "./components/AppShell";
import { ArchivePage } from "./pages/ArchivePage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RunsPage } from "./pages/RunsPage";

const queryClient = new QueryClient();

function RequireAuth({ children }: { children: ReactElement }) {
  const location = useLocation();
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: () => api.getSession(),
  });

  if (sessionQuery.isLoading) {
    return <div className="empty-state">Checking dashboard session...</div>;
  }

  if (sessionQuery.error || !sessionQuery.data) {
    return (
      <div className="inline-alert inline-alert-danger">
        {(sessionQuery.error as Error | undefined)?.message ?? "Failed to load dashboard session."}
      </div>
    );
  }

  if (!sessionQuery.data.authenticated) {
    return (
      <Navigate
        to="/admin/login"
        replace
        state={{ from: `${location.pathname}${location.search}${location.hash}` }}
      />
    );
  }

  return children;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/waitlist" element={<HomePage initialWaitlistOpen />} />
      <Route path="/login" element={<Navigate to="/admin/login" replace />} />
      <Route path="/archive" element={<Navigate to="/admin/archive" replace />} />
      <Route path="/runs" element={<Navigate to="/admin/runs" replace />} />
      <Route path="/admin/login" element={<LoginPage />} />
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <AppShell title="Overview">
              <OverviewPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/admin/archive"
        element={
          <RequireAuth>
            <AppShell title="Archive">
              <ArchivePage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/admin/runs"
        element={
          <RequireAuth>
            <AppShell title="Runs">
              <RunsPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route path="/admin/*" element={<Navigate to="/admin" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
