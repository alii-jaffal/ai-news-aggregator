import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { LoginPage } from "./LoginPage";
import { renderWithProviders } from "../test/test-utils";

vi.mock("../api", () => ({
  api: {
    getSession: vi.fn(),
    login: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("LoginPage", () => {
  beforeEach(() => {
    mockedApi.getSession.mockResolvedValue({
      authenticated: false,
      username: null,
    });
    mockedApi.login.mockResolvedValue({
      authenticated: true,
      username: "admin",
    });
  });

  it("submits dashboard credentials", async () => {
    renderWithProviders(<LoginPage />, ["/login"]);

    await userEvent.type(await screen.findByLabelText(/username/i), "admin");
    await userEvent.type(screen.getByLabelText(/password/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockedApi.login).toHaveBeenCalledWith({
        username: "admin",
        password: "secret",
      });
    });
  });
});
