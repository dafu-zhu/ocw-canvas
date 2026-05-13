import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface Crumb {
  label: string;
  to?: string;
}

export function AppLayout({ crumbs, children }: { crumbs: Crumb[]; children: ReactNode }) {
  const { user, teacherMode, setTeacherMode, logout } = useAuth();
  const nav = useNavigate();

  async function doLogout() {
    await logout();
    nav("/login");
  }

  return (
    <div className="app">
      <nav className="left-rail">
        <div className="brand">OCW</div>
        <button
          className="rail-item"
          onClick={() => setTeacherMode(!teacherMode)}
          title="Toggle teacher mode"
        >
          <span className="glyph">{teacherMode ? "🛠" : "👤"}</span>
          {user ? user.display_name.split(" ")[0] : "Account"}
        </button>
        <RailLink to="/" glyph="🏠" label="Dashboard" />
        <RailLink to="/courses" glyph="📚" label="Courses" />
        <RailLink to="/calendar" glyph="📅" label="Calendar" />
        <RailLink to="/announcements" glyph="📨" label="Inbox" />
        <div className="spacer" />
        <button className="rail-item" onClick={doLogout}>
          <span className="glyph">⎋</span>Log out
        </button>
      </nav>
      <div className="main">
        <div className="breadcrumb">
          {crumbs.map((c, i) => (
            <span key={i}>
              {i > 0 && <span className="sep">›</span>}
              {c.to ? <NavLink to={c.to}>{c.label}</NavLink> : <span className="leaf">{c.label}</span>}
            </span>
          ))}
        </div>
        {children}
      </div>
    </div>
  );
}

function RailLink({ to, glyph, label }: { to: string; glyph: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => "rail-item" + (isActive ? " active" : "")}
      end={to === "/"}
    >
      <span className="glyph">{glyph}</span>
      {label}
    </NavLink>
  );
}
