import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "editor" | "viewer";
  is_active: boolean;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
    }),
    { name: "nexus-auth" }
  )
);

/** Read token outside React (for api.ts request interceptor). */
export function getStoredToken(): string | null {
  try {
    const raw = localStorage.getItem("nexus-auth");
    return raw ? (JSON.parse(raw) as { state: { token: string | null } }).state.token : null;
  } catch {
    return null;
  }
}
