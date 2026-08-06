import type { ReactNode } from "react";

import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./App";
import { api } from "./api";
import { renderWithProviders } from "./test/test-utils";

vi.mock("./api", () => ({
  api: {
    getSession: vi.fn(),
  },
}));

vi.mock("./components/AppShell", () => ({
  AppShell: ({ title, children }: { title: string; children: ReactNode }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("./pages/HomePage", () => ({
  HomePage: ({ initialWaitlistOpen = false }: { initialWaitlistOpen?: boolean }) => (
    <div>{initialWaitlistOpen ? "Public homepage waitlist open" : "Public homepage"}</div>
  ),
}));

vi.mock("./pages/LoginPage", () => ({
  LoginPage: () => <div>Admin login</div>,
}));

vi.mock("./pages/OverviewPage", () => ({
  OverviewPage: () => <div>Overview page</div>,
}));

vi.mock("./pages/ArchivePage", () => ({
  ArchivePage: () => <div>Archive page</div>,
}));

vi.mock("./pages/RunsPage", () => ({
  RunsPage: () => <div>Runs page</div>,
}));

const mockedApi = vi.mocked(api);

describe("AppRoutes", () => {
  beforeEach(() => {
    mockedApi.getSession.mockReset();
  });

  it("renders the public homepage at root without auth", async () => {
    renderWithProviders(<AppRoutes />, ["/"]);

    expect(await screen.findByText("Public homepage")).toBeInTheDocument();
  });

  it("renders the waitlist placeholder publicly", async () => {
    renderWithProviders(<AppRoutes />, ["/waitlist"]);

    expect(await screen.findByText("Public homepage waitlist open")).toBeInTheDocument();
  });

  it("renders the admin login page at /admin/login", async () => {
    mockedApi.getSession.mockResolvedValue({
      authenticated: false,
      username: null,
    });

    renderWithProviders(<AppRoutes />, ["/admin/login"]);

    expect(await screen.findByText("Admin login")).toBeInTheDocument();
  });

  it("redirects unauthenticated /admin traffic to /admin/login", async () => {
    mockedApi.getSession.mockResolvedValue({
      authenticated: false,
      username: null,
    });

    renderWithProviders(<AppRoutes />, ["/admin"]);

    expect(await screen.findByText("Admin login")).toBeInTheDocument();
  });

  it("redirects /login to /admin/login", async () => {
    mockedApi.getSession.mockResolvedValue({
      authenticated: false,
      username: null,
    });

    renderWithProviders(<AppRoutes />, ["/login"]);

    expect(await screen.findByText("Admin login")).toBeInTheDocument();
  });

  it("redirects legacy /archive to /admin/archive and keeps the dashboard protected", async () => {
    mockedApi.getSession.mockResolvedValue({
      authenticated: true,
      username: "admin",
    });

    renderWithProviders(<AppRoutes />, ["/archive"]);

    expect(await screen.findByText("Archive")).toBeInTheDocument();
    expect(screen.getByText("Archive page")).toBeInTheDocument();
  });
});
