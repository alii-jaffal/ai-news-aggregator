import { Database, LayoutDashboard, PlayCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink } from "react-router-dom";
import { type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { BrandMark } from "./BrandMark";

interface AppShellProps {
  title: string;
  toolbar?: ReactNode;
  children: ReactNode;
}

const navItems = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard },
  { to: "/admin/archive", label: "Archive", icon: Database },
  { to: "/admin/runs", label: "Runs", icon: PlayCircle },
];

export function AppShell({ title, toolbar, children }: AppShellProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: () => api.getSession(),
  });
  const logoutMutation = useMutation({
    mutationFn: () => api.logout(),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["session"] }),
        queryClient.invalidateQueries({ queryKey: ["overview"] }),
        queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] }),
      ]);
      navigate("/admin/login", { replace: true });
    },
  });

  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar">
        <div className="app-brand">
          <BrandMark className="app-brand__mark" />
          <div>
            <strong>Stag</strong>
            <span>Private admin console</span>
          </div>
        </div>
        <nav className="app-nav">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                isActive ? "app-nav__link app-nav__link-active" : "app-nav__link"
              }
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="app-shell__main">
        <header className="app-toolbar">
          <div>
            <p className="app-toolbar__eyebrow">Private admin view</p>
            <h1>{title}</h1>
          </div>
          <div className="app-toolbar__actions">
            {toolbar}
            {sessionQuery.data?.authenticated ? (
              <>
                <span className="toolbar-user-chip">{sessionQuery.data.username}</span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={logoutMutation.isPending}
                  onClick={() => void logoutMutation.mutateAsync()}
                >
                  {logoutMutation.isPending ? "Signing out..." : "Sign out"}
                </button>
              </>
            ) : null}
          </div>
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
