import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";
import { clearTokens } from "../auth/tokenStorage";
import { LoginPage } from "./LoginPage";

vi.mock("../api/auth");

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<p>Bookmarks home</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    clearTokens();
    vi.mocked(authApi.login).mockReset();
    vi.mocked(authApi.fetchCurrentUser).mockReset();
  });

  it("logs in and navigates home on success", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: "1",
      email: "user@example.com",
      created_at: new Date().toISOString(),
    });

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-1");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => {
      expect(screen.getByText("Bookmarks home")).toBeInTheDocument();
    });
    expect(authApi.login).toHaveBeenCalledWith("user@example.com", "correct-horse-1");
  });

  it("shows an error message when login fails", async () => {
    vi.mocked(authApi.login).mockRejectedValue(new ApiError(401, "Invalid email or password"));

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });
});
