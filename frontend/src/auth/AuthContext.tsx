import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, api } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  teacherMode: boolean;
  setTeacherMode: (v: boolean) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  unreadCount: number;
  refreshUnread: () => void;
}

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [teacherMode, setTeacherModeState] = useState(
    () => localStorage.getItem("teacherMode") === "1",
  );

  const refreshUnread = useCallback(() => {
    api
      .getUnreadCount()
      .then((r) => setUnreadCount(r.count))
      .catch(() => setUnreadCount(0));
  }, []);

  useEffect(() => {
    api
      .me()
      .then((u) => {
        setUser(u);
        refreshUnread();
      })
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) console.error(e);
      })
      .finally(() => setLoading(false));
  }, [refreshUnread]);

  function setTeacherMode(v: boolean) {
    setTeacherModeState(v);
    localStorage.setItem("teacherMode", v ? "1" : "0");
  }

  async function login(email: string, password: string) {
    setUser(await api.login(email, password));
    refreshUnread();
  }
  async function logout() {
    await api.logout();
    setUser(null);
    setUnreadCount(0);
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      teacherMode,
      setTeacherMode,
      login,
      logout,
      unreadCount,
      refreshUnread,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, loading, teacherMode, unreadCount, refreshUnread],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
