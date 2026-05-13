import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppLayout } from "../components/AppLayout";
import { Spinner } from "../components/Spinner";
import { CourseEditModal } from "../components/edit/CourseEditModal";

export function DashboardPage() {
  const { teacherMode } = useAuth();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [editing, setEditing] = useState<Course | "new" | null>(null);

  function reload() {
    api.listCourses().then(setCourses);
  }
  useEffect(reload, []);

  return (
    <AppLayout crumbs={[{ label: "Dashboard" }]}>
      <div className="content">
        <div className="page-with-sidebar">
          <div className="col-main">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h1 className="page-title">Dashboard</h1>
              {teacherMode && (
                <button className="btn primary" onClick={() => setEditing("new")}>
                  + Add course
                </button>
              )}
            </div>
            {courses === null ? (
              <Spinner />
            ) : courses.length === 0 ? (
              <div className="center-empty">Add your first course to get started.</div>
            ) : (
              <div className="dashboard-grid">
                {courses.map((c) => (
                  <div className="course-card" key={c.id}>
                    <div className="band" style={{ background: c.color }}>
                      {teacherMode && (
                        <span className="menu" onClick={() => setEditing(c)} title="Edit course">
                          ⋮
                        </span>
                      )}
                    </div>
                    <div className="body">
                      <Link to={`/courses/${c.id}`} className="ctitle">
                        {c.code} {c.term_label && `(${c.term_label})`} {c.title}
                      </Link>
                      <div className="csub">{c.title}</div>
                      <div className="cterm">{c.institution || c.term_label}</div>
                    </div>
                    <div className="footer-icons">
                      <Link to={`/courses/${c.id}/announcements`} title="Announcements">
                        📣
                      </Link>
                      <Link to={`/courses/${c.id}/modules`} title="Modules">
                        📂
                      </Link>
                      <Link to={`/courses/${c.id}/assignments`} title="Assignments">
                        📝
                      </Link>
                      <Link to={`/courses/${c.id}/grades`} title="Grades">
                        📊
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="col-side">
            <div className="widget">
              <h2>To Do</h2>
              <div className="muted" style={{ fontSize: 13 }}>
                Upcoming assignment deadlines will appear here.
              </div>
            </div>
            <div className="widget">
              <h2>Recent Feedback</h2>
              <div className="muted" style={{ fontSize: 13 }}>
                Graded work will appear here.
              </div>
            </div>
          </div>
        </div>
      </div>
      {editing && (
        <CourseEditModal
          course={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </AppLayout>
  );
}
