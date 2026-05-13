import { useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    if (!token) {
      setErr("Missing or invalid reset link.");
      return;
    }
    if (pw.length < 6) {
      setErr("Password must be at least 6 characters.");
      return;
    }
    if (pw !== confirm) {
      setErr("Passwords don't match.");
      return;
    }
    setBusy(true);
    try {
      await api.resetPassword(token, pw);
      // The session cookie is now set — hard-navigate so the app re-reads /auth/me.
      window.location.assign(import.meta.env.BASE_URL || "/");
    } catch {
      setErr("That reset link is invalid or has expired. Request a new one from the login page.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>Set a new password</h1>
        <label htmlFor="pw">New password</label>
        <input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus />
        <label htmlFor="cf">Confirm password</label>
        <input
          id="cf"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        {err && <div className="err">{err}</div>}
        <div className="actions">
          <button className="btn primary" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Saving…" : "Set password & sign in"}
          </button>
        </div>
      </form>
    </div>
  );
}
