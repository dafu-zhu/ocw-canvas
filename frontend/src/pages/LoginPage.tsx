import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [sent, setSent] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (forgot) {
        await api.forgotPassword(email);
        setSent(true);
      } else {
        await login(email, password);
        nav("/");
      }
    } catch {
      setErr(forgot ? "Couldn't send the reset email." : "Invalid email or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>OCW Canvas</h1>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
        />
        {!forgot && (
          <>
            <label htmlFor="pw">Password</label>
            <input
              id="pw"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </>
        )}
        {err && <div className="err">{err}</div>}
        {sent && (
          <div className="muted" style={{ fontSize: 13 }}>
            If that email is registered, a reset link is on its way.
          </div>
        )}
        <div className="actions">
          <button className="btn primary" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Working…" : forgot ? "Email me a reset link" : "Sign in"}
          </button>
          <button
            type="button"
            className="linklike"
            style={{ background: "none", border: "none", cursor: "pointer", color: "#0374b5" }}
            onClick={() => {
              setForgot(!forgot);
              setErr("");
              setSent(false);
            }}
          >
            {forgot ? "Back to sign in" : "Forgot password?"}
          </button>
        </div>
      </form>
    </div>
  );
}
