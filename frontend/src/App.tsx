import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ArchivePage } from "./pages/ArchivePage";
import { OverviewPage } from "./pages/OverviewPage";
import { RunsPage } from "./pages/RunsPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <AppShell title="Overview">
                <OverviewPage />
              </AppShell>
            }
          />
          <Route
            path="/archive"
            element={
              <AppShell title="Archive">
                <ArchivePage />
              </AppShell>
            }
          />
          <Route
            path="/runs"
            element={
              <AppShell title="Runs">
                <RunsPage />
              </AppShell>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
