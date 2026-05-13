import { useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";

function Mark({ size = 28 }: { size?: number }) {
  const r = size / 2 - 2;
  const cx = size / 2;
  const cy = size / 2;
  const ticks = Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4;
    const x1 = cx + Math.cos(a) * (r - 4);
    const y1 = cy + Math.sin(a) * (r - 4);
    const x2 = cx + Math.cos(a) * r;
    const y2 = cy + Math.sin(a) * r;
    return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1.5" />;
  });
  return (
    <svg className="glyph" viewBox={`0 0 ${size} ${size}`} aria-hidden>
      <circle cx={cx} cy={cy} r={r - 6} fill="none" stroke="currentColor" strokeWidth="1.5" />
      {ticks}
    </svg>
  );
}

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
      <div className="login-mark">
        <Mark />
        OCW CANVAS
      </div>
      <form className="login-card" onSubmit={submit}>
        <h1>Set a new password</h1>
        <label htmlFor="pw">New password</label>
        <input
          id="pw"
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          autoFocus
          autoComplete="new-password"
        />
        <label htmlFor="cf">Confirm password</label>
        <input
          id="cf"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
        />
        {err && <div className="err">{err}</div>}
        <div className="check-row">
          <span />
          <button className="btn-canvas" disabled={busy}>
            {busy ? "Saving…" : "Set password & sign in"}
          </button>
        </div>
      </form>
    </div>
  );
}
