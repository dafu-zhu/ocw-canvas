import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Spinner } from "./Spinner";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Loading OCW Canvas…" />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
