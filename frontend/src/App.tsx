import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactElement } from "react";

import { api } from "./api";
import { AppShell } from "./components/AppShell";
import { ArchivePage } from "./pages/ArchivePage";
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
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <AppShell title="Overview">
                  <OverviewPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/archive"
            element={
              <RequireAuth>
                <AppShell title="Archive">
                  <ArchivePage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/runs"
            element={
              <RequireAuth>
                <AppShell title="Runs">
                  <RunsPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
