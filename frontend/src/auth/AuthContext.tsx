import { useEffect, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { refreshAccessToken } from "../api/client";
import type { UserRead } from "../api/types";
import { clearTokens, getRefreshToken, setAccessToken, setRefreshToken } from "./tokenStorage";
import { AuthContext, type AuthContextValue } from "./useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On a fresh page load there's no access token in memory - only the
  // refresh token survives in localStorage. Trade it for a fresh access
  // token before deciding whether the visitor is logged in.
  useEffect(() => {
    void (async () => {
      if (!getRefreshToken()) {
        setIsLoading(false);
        return;
      }
      const newAccessToken = await refreshAccessToken();
      if (!newAccessToken) {
        setIsLoading(false);
        return;
      }
      try {
        setUser(await authApi.fetchCurrentUser());
      } catch {
        clearTokens();
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  async function login(email: string, password: string): Promise<void> {
    const tokens = await authApi.login(email, password);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    setUser(await authApi.fetchCurrentUser());
  }

  async function register(email: string, password: string): Promise<void> {
    await authApi.register(email, password);
    await login(email, password);
  }

  async function logout(): Promise<void> {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // Best-effort - clear local state regardless of whether the
        // server call succeeds, so a flaky network never traps a user
        // in a logged-in-looking-but-broken state.
      }
    }
    clearTokens();
    setUser(null);
  }

  const value: AuthContextValue = { user, isLoading, login, register, logout };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
