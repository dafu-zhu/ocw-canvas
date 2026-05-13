import { createContext, useContext, useEffect, useMemo, useState } from "react";
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
}

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [teacherMode, setTeacherModeState] = useState(
    () => localStorage.getItem("teacherMode") === "1",
  );

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) console.error(e);
      })
      .finally(() => setLoading(false));
  }, []);

  function setTeacherMode(v: boolean) {
    setTeacherModeState(v);
    localStorage.setItem("teacherMode", v ? "1" : "0");
  }

  async function login(email: string, password: string) {
    setUser(await api.login(email, password));
  }
  async function logout() {
    await api.logout();
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, loading, teacherMode, setTeacherMode, login, logout }),
    [user, loading, teacherMode],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
