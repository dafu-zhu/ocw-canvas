import { Link } from "react-router-dom";

export interface TodoEntry {
  key: string;
  title: string;
  to: string;
  courseName?: string;
  points?: number;
  dueAt?: string | null;
}

export function TodoList({ entries, empty }: { entries: TodoEntry[]; empty: string }) {
  if (entries.length === 0) {
    return (
      <div className="muted" style={{ fontSize: 13 }}>
        {empty}
      </div>
    );
  }
  return (
    <>
      {entries.map((e) => (
        <div className="todo-item" key={e.key}>
          <span className="glyph">📝</span>
          <span>
            <Link to={e.to}>{e.title}</Link>
            <div className="meta">
              {e.courseName ? `${e.courseName} · ` : ""}
              {e.points != null ? `${e.points} points` : ""}
              {e.points != null && e.dueAt ? " · " : ""}
              {e.dueAt ? new Date(e.dueAt).toLocaleString() : ""}
            </div>
          </span>
        </div>
      ))}
    </>
  );
}
