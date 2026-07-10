import { request } from "./client";
import type { TokenPair, UserRead } from "./types";

export async function register(email: string, password: string): Promise<UserRead> {
  return request<UserRead>("/auth/register", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function login(email: string, password: string): Promise<TokenPair> {
  return request<TokenPair>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function logout(refreshToken: string): Promise<void> {
  await request<void>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    auth: false,
  });
}

export async function fetchCurrentUser(): Promise<UserRead> {
  return request<UserRead>("/auth/me");
}
