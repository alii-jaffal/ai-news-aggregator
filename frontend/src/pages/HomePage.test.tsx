import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { renderWithProviders } from "../test/test-utils";
import { HomePage } from "./HomePage";

vi.mock("../api", () => ({
  api: {
    joinWaitlist: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("HomePage", () => {
  beforeEach(() => {
    mockedApi.joinWaitlist.mockResolvedValue({
      email: "reader@example.com",
      created_at: "2026-08-06T12:00:00Z",
      already_registered: false,
    });
  });

  it("renders the ZIP-based public homepage and submits the waitlist form", async () => {
    renderWithProviders(<HomePage />);

    expect(screen.getByText(/personalized ai news, once a week/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /keep up with ai\./i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /a simple weekly routine\./i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /your week in ai, without the noise\./i })).toBeInTheDocument();
    expect(screen.getByText(/ai news, made personal\./i)).toBeInTheDocument();
    expect(screen.queryByText(/admin sign in/i)).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/email address/i), "reader@example.com");
    await userEvent.click(screen.getByRole("button", { name: /join waitlist/i }));

    await waitFor(() => {
      expect(mockedApi.joinWaitlist).toHaveBeenCalledWith({
        email: "reader@example.com",
      });
    });

    expect(screen.getByRole("status")).toHaveTextContent(/you're on the waitlist\./i);
  });
});
