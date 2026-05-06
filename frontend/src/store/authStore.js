import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authAPI } from "../services/api";

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      // ------------------------------------------------------------------
      // login
      // ------------------------------------------------------------------
      login: async (email, password) => {
        const data = await authAPI.login(email, password);
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          isAuthenticated: true,
        });
        return data;
      },

      // ------------------------------------------------------------------
      // register
      // ------------------------------------------------------------------
      register: async (email, password, fullName) => {
        const data = await authAPI.register(email, password, fullName);
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        set({
          user: data.user,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          isAuthenticated: true,
        });
        return data;
      },

      // ------------------------------------------------------------------
      // logout
      // ------------------------------------------------------------------
      logout: async () => {
        try {
          await authAPI.logout();
        } catch {
          // Ignore — token may already be expired
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      // ------------------------------------------------------------------
      // loadUser — call on app init to hydrate user from a stored token
      // ------------------------------------------------------------------
      loadUser: async () => {
        const token = localStorage.getItem("access_token");
        if (!token) return;
        try {
          const user = await authAPI.me();
          set({ user, isAuthenticated: true });
        } catch {
          // Token invalid or expired — clear everything
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
        }
      },

      // Legacy setters kept for backward compatibility with interceptor
      setTokens: (token, refreshToken) => {
        localStorage.setItem("access_token", token);
        localStorage.setItem("refresh_token", refreshToken);
        set({ accessToken: token, refreshToken, isAuthenticated: true });
      },
      setUser: (user) => set({ user }),
    }),
    {
      name: "auth-storage",
      // Only persist tokens and user — not action functions
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
