import { Database, Inbox, LayoutDashboard, PlayCircle } from "lucide-react";
import { NavLink } from "react-router-dom";
import { type ReactNode } from "react";

interface AppShellProps {
  title: string;
  toolbar?: ReactNode;
  children: ReactNode;
}

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/archive", label: "Archive", icon: Database },
  { to: "/runs", label: "Runs", icon: PlayCircle },
];

export function AppShell({ title, toolbar, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar">
        <div className="app-brand">
          <div className="app-brand__mark">
            <Inbox size={18} />
          </div>
          <div>
            <strong>AI News Aggregator</strong>
            <span>Demo dashboard</span>
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
            <p className="app-toolbar__eyebrow">Local admin view</p>
            <h1>{title}</h1>
          </div>
          <div className="app-toolbar__actions">{toolbar}</div>
        </header>
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
