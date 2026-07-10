import { createContext, useContext } from "react";
import type { UserRead } from "../api/types";

export interface AuthContextValue {
  user: UserRead | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

// Defined here (not in AuthContext.tsx) so this file has no component
// export, keeping it clear of react-refresh's only-export-components rule.
// A name like "authContext.ts" alongside "AuthContext.tsx" would differ
// only by case and file extension - fine on case-sensitive Linux CI, but
// an easy source of "works on my machine" bugs on case-insensitive
// filesystems (Windows, default macOS).
export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
