import { screen, waitFor, within } from "@testing-library/react";
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

  it("renders the minimal product message and opens the waitlist modal", async () => {
    renderWithProviders(<HomePage />);

    expect(
      screen.getByRole("heading", {
        name: /your personalized weekly ai briefing\./i,
      })
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /less noise\. more signal\./i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /stay informed without chasing every update\./i })
    ).toBeInTheDocument();
    expect(screen.getByText(/personalized weekly ai news, made simple\./i)).toBeInTheDocument();
    expect(screen.queryByText(/admin sign in/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/duplicate coverage/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/canonical/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/clustering/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/digest per story/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: /join the waitlist/i })[0]);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText(/email address/i), "reader@example.com");
    await userEvent.click(within(dialog).getByRole("button", { name: /^join the waitlist$/i }));

    await waitFor(() => {
      expect(mockedApi.joinWaitlist).toHaveBeenCalledWith({
        email: "reader@example.com",
      });
    });
    expect(screen.getByText(/you have been added to the waitlist\./i)).toBeInTheDocument();
  });
});
