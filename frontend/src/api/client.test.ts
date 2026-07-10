import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearTokens, setAccessToken, setRefreshToken } from "../auth/tokenStorage";
import { ApiError, refreshAccessToken, request } from "./client";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("request", () => {
  beforeEach(() => {
    clearTokens();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the Authorization header when an access token is present", async () => {
    setAccessToken("token-abc");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await request("/bookmarks");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer token-abc");
  });

  it("does not attach Authorization when auth: false", async () => {
    setAccessToken("token-abc");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await request("/auth/login", { method: "POST", auth: false });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("throws ApiError with the parsed detail message on a non-2xx response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: "Email is already registered" }, { status: 409 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/auth/register", { method: "POST", auth: false })).rejects.toMatchObject({
      status: 409,
      message: "Email is already registered",
    });
  });

  it("on a 401, refreshes the token once and retries the original request", async () => {
    setAccessToken("expired-token");
    setRefreshToken("valid-refresh-token");

    const fetchMock = vi
      .fn()
      // First call: the original request, rejected as unauthorized.
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      // Second call: POST /auth/refresh succeeds.
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-token",
          refresh_token: "new-refresh",
          token_type: "bearer",
        })
      )
      // Third call: the retried original request succeeds.
      .mockResolvedValueOnce(jsonResponse({ id: "1" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await request<{ id: string }>("/bookmarks/1");

    expect(result).toEqual({ id: "1" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const refreshCall = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(refreshCall[0]).toMatch(/\/auth\/refresh$/);
    const retryCall = fetchMock.mock.calls[2] as [string, RequestInit];
    const retryHeaders = retryCall[1].headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer new-token");
  });

  it("does not retry a second time if the refreshed request still 401s", async () => {
    setAccessToken("expired-token");
    setRefreshToken("valid-refresh-token");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-token",
          refresh_token: "new-refresh",
          token_type: "bearer",
        })
      )
      .mockResolvedValueOnce(new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/bookmarks/1")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

describe("refreshAccessToken", () => {
  beforeEach(() => {
    clearTokens();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns null without calling fetch when there is no stored refresh token", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await refreshAccessToken();

    expect(result).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shares one in-flight refresh call across concurrent callers", async () => {
    setRefreshToken("valid-refresh-token");
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        access_token: "new-token",
        refresh_token: "new-refresh",
        token_type: "bearer",
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const [first, second] = await Promise.all([refreshAccessToken(), refreshAccessToken()]);

    expect(first).toBe("new-token");
    expect(second).toBe("new-token");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
