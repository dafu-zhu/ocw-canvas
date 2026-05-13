import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Announcement } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppLayout } from "../components/AppLayout";
import { CourseLayout } from "../components/CourseLayout";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

function preview(md: string, n = 180): string {
  const t = md.replace(/[#>*`_]/g, "").replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n) + "…" : t;
}

export function AnnouncementsPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  const { refreshUnread } = useAuth();
  const [items, setItems] = useState<Announcement[] | null>(null);
  const [open, setOpen] = useState<Announcement | null>(null);
  const [search, setSearch] = useState("");

  function reload() {
    api.listAnnouncements(courseId).then(setItems);
  }
  useEffect(reload, [courseId]);

  const filtered = useMemo(() => {
    if (!items) return [];
    const q = search.toLowerCase().trim();
    return q
      ? items.filter(
          (a) => a.title.toLowerCase().includes(q) || a.body_md.toLowerCase().includes(q),
        )
      : items;
  }, [items, search]);

  async function openAnnouncement(a: Announcement) {
    setOpen(a);
    if (a.read_at == null) {
      await api.markRead(a.id);
      refreshUnread();
      reload();
    }
  }

  async function markAll() {
    await api.markAllRead(courseId);
    refreshUnread();
    reload();
  }

  const body = (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Announcements</h1>
        <div>
          <input
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ marginRight: 8 }}
          />
          <button className="btn" onClick={markAll}>
            Mark All as Read
          </button>
        </div>
      </div>
      {items === null ? (
        <Spinner />
      ) : filtered.length === 0 ? (
        <div className="center-empty">No announcements yet.</div>
      ) : (
        <div>
          {filtered.map((a) => (
            <div
              key={a.id}
              onClick={() => openAnnouncement(a)}
              style={{
                display: "flex",
                gap: 12,
                padding: "12px 4px",
                borderBottom: "1px solid #eee",
                cursor: "pointer",
                background: open?.id === a.id ? "#f7f9fb" : undefined,
              }}
            >
              <div
                aria-hidden
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  background: "#0374b5",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                AI
              </div>
              <div style={{ flex: 1 }}>
                <div>
                  {a.read_at == null && (
                    <span
                      style={{
                        display: "inline-block",
                        width: 8,
                        height: 8,
                        borderRadius: 4,
                        background: "#0374b5",
                        marginRight: 6,
                      }}
                    />
                  )}
                  <strong>{a.title}</strong>
                </div>
                {open?.id === a.id ? (
                  <div style={{ marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
                    <Markdown>{a.body_md}</Markdown>
                    {a.related_assignment_id && a.course_id && (
                      <Link
                        to={`/courses/${a.course_id}/assignments/${a.related_assignment_id}`}
                        className="btn small"
                      >
                        Open assignment
                      </Link>
                    )}
                  </div>
                ) : (
                  <div className="muted" style={{ fontSize: 13 }}>
                    {preview(a.body_md)}
                  </div>
                )}
              </div>
              <div className="muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                Posted on:
                <br />
                {new Date(a.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );

  if (courseId) {
    if (!course) return <Spinner />;
    return (
      <CourseLayout course={course} section="Announcements">
        {body}
      </CourseLayout>
    );
  }
  return (
    <AppLayout crumbs={[{ label: "Inbox" }]}>
      <div className="content">{body}</div>
    </AppLayout>
  );
}
