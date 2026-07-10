// The access token lives in memory only (module-level variable) - it never
// touches localStorage, so it can't be read by an XSS payload that persists
// across page loads. It's simply gone on refresh, which is fine: the
// refresh token (below) gets a new one automatically on app bootstrap.
//
// The refresh token *does* go in localStorage. The backend issues it as a
// plain JSON field rather than an httpOnly cookie (see ARCHITECTURE.md),
// so there's no way to store it that's invisible to JS - localStorage is
// the pragmatic choice here, not a "solved" one. Rotation + reuse
// detection on the backend is what limits the blast radius of that
// trade-off, not this storage choice.
const REFRESH_TOKEN_KEY = "bookmarks.refresh_token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearTokens(): void {
  accessToken = null;
  setRefreshToken(null);
}
