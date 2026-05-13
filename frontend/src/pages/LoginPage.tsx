import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function Mark({ size = 28 }: { size?: number }) {
  // A small ringed/asterisk logo, in the spirit of Canvas's wordmark glyph.
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

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [stay, setStay] = useState(false);
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
      <div className="login-mark">
        <Mark />
        OCW CANVAS
      </div>

      <form className="login-card" onSubmit={submit}>
        <h1 className="sr-only">Sign in to OCW Canvas</h1>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
          autoComplete="email"
          required
        />

        {!forgot && (
          <>
            <label htmlFor="pw">Password</label>
            <input
              id="pw"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </>
        )}

        <div className="check-row">
          {!forgot ? (
            <label className="stay">
              <input type="checkbox" checked={stay} onChange={(e) => setStay(e.target.checked)} />
              Stay signed in
            </label>
          ) : (
            <span />
          )}
          <button className="btn-canvas" disabled={busy}>
            {busy ? "…" : forgot ? "Email me a reset link" : "Log In"}
          </button>
        </div>

        <button
          type="button"
          className="forgot"
          onClick={() => {
            setForgot(!forgot);
            setErr("");
            setSent(false);
          }}
        >
          {forgot ? "Back to sign in" : "Forgot Password?"}
        </button>

        {err && <div className="err">{err}</div>}
        {sent && (
          <div className="info">
            If that email is registered, a reset link is on its way.
          </div>
        )}
      </form>

      <div className="login-foot">
        <span>
          <a href="https://github.com/dafu-zhu/ocw-canvas#readme" target="_blank" rel="noreferrer">
            Help
          </a>
          <a
            href="https://github.com/dafu-zhu/ocw-canvas/blob/master/README.md"
            target="_blank"
            rel="noreferrer"
          >
            Privacy Policy
          </a>
          <a
            href="https://github.com/dafu-zhu/ocw-canvas/blob/master/README.md"
            target="_blank"
            rel="noreferrer"
          >
            Cookie Notice
          </a>
          <a
            href="https://github.com/dafu-zhu/ocw-canvas/blob/master/README.md"
            target="_blank"
            rel="noreferrer"
          >
            Acceptable Use Policy
          </a>
        </span>
        <div className="brand-mark">
          <Mark size={16} />
          OCW CANVAS
        </div>
      </div>
    </div>
  );
}
