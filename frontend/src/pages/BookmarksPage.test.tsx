import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as bookmarksApi from "../api/bookmarks";
import * as useAuthModule from "../auth/useAuth";
import { BookmarksPage } from "./BookmarksPage";

vi.mock("../api/bookmarks");
vi.mock("../auth/useAuth");

const now = new Date().toISOString();

describe("BookmarksPage", () => {
  beforeEach(() => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      user: { id: "1", email: "user@example.com", created_at: now },
      isLoading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    });
  });

  it("renders bookmarks returned by the API", async () => {
    vi.mocked(bookmarksApi.listBookmarks).mockResolvedValue({
      items: [
        {
          id: "1",
          url: "https://example.com",
          title: "Example",
          description: null,
          tags: ["reading"],
          created_at: now,
          updated_at: now,
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });

    render(
      <MemoryRouter>
        <BookmarksPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Example")).toBeInTheDocument();
    expect(screen.getByText("reading")).toBeInTheDocument();
  });

  it("removes a bookmark from the list after deleting it", async () => {
    vi.mocked(bookmarksApi.listBookmarks).mockResolvedValue({
      items: [
        {
          id: "1",
          url: "https://example.com",
          title: "Example",
          description: null,
          tags: [],
          created_at: now,
          updated_at: now,
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });
    vi.mocked(bookmarksApi.deleteBookmark).mockResolvedValue(undefined);

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <BookmarksPage />
      </MemoryRouter>
    );

    await screen.findByText("Example");
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.queryByText("Example")).not.toBeInTheDocument();
    });
  });
});
