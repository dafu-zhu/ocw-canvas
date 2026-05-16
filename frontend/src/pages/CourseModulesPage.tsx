import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CourseDetail, Module, ModuleItem } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { ModuleEditModal, ModuleItemEditModal } from "../components/edit/ModuleEditModals";
import { useCourse } from "../lib/useCourse";

const ICON: Record<string, string> = {
  link: "🔗",
  video: "🔗",
  assignment: "📝",
  note: "📄",
  header: "›",
};

export function CourseModulesPage() {
  const { courseId } = useParams();
  const { course, reload } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [editingModule, setEditingModule] = useState<Module | "new" | null>(null);
  const [editingItem, setEditingItem] = useState<{
    moduleId: string;
    item: ModuleItem | "new";
  } | null>(null);

  if (!course) return <Spinner />;

  function toggle(id: string) {
    setCollapsed((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function removeModule(id: string) {
    if (confirm("Delete module and its items?")) {
      await api.deleteModule(id);
      reload();
    }
  }
  async function removeItem(id: string) {
    if (confirm("Delete item?")) {
      await api.deleteItem(id);
      reload();
    }
  }

  return (
    <CourseLayout course={course} section="Modules">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Modules</h1>
        <div>
          <button
            className="btn"
            onClick={() => setCollapsed(new Set(course.modules.map((m) => m.id)))}
          >
            Collapse All
          </button>
          {teacherMode && (
            <button
              className="btn primary"
              style={{ marginLeft: 8 }}
              onClick={() => setEditingModule("new")}
            >
              + Module
            </button>
          )}
        </div>
      </div>
      {course.modules.length === 0 && <div className="center-empty">No modules yet.</div>}
      {course.modules.map((m) => {
        // Per feedback-module-content-chapter-readings Rule 1: kind="video"
        // items belong on the Video Lectures page, not in the Modules view.
        // Teacher mode still sees everything so the items remain editable.
        const visibleItems = teacherMode
          ? m.items
          : m.items.filter((it) => it.kind !== "video");
        if (visibleItems.length === 0 && !teacherMode) return null;
        return (
        <div className="module" key={m.id}>
          <div className="module-head" onClick={() => toggle(m.id)}>
            <span>{collapsed.has(m.id) ? "▸" : "▾"}</span>
            <span style={{ flex: 1 }}>{m.title}</span>
            {teacherMode && (
              <span className="row-actions" onClick={(e) => e.stopPropagation()}>
                <button
                  className="btn small"
                  onClick={() => setEditingItem({ moduleId: m.id, item: "new" })}
                >
                  + Item
                </button>
                <button className="btn small" onClick={() => setEditingModule(m)}>
                  Edit
                </button>
                <button className="btn small" onClick={() => removeModule(m.id)}>
                  Delete
                </button>
              </span>
            )}
          </div>
          {!collapsed.has(m.id) &&
            visibleItems.map((it) => (
              <div
                className={`module-item indent-${it.indent} ${it.kind === "header" ? "header-row" : ""}`}
                key={it.id}
              >
                <span className="mi-icon">{ICON[it.kind] ?? "•"}</span>
                <span style={{ flex: 1 }}>
                  {it.kind === "header" ? (
                    <strong>{it.title}</strong>
                  ) : it.kind === "link" || it.kind === "video" ? (
                    <a
                      href={it.external_url}
                      target="_blank"
                      rel="noreferrer"
                      className="external-arrow"
                    >
                      {it.title}
                    </a>
                  ) : it.kind === "assignment" && it.assignment_id ? (
                    <Link to={`/courses/${course.id}/assignments/${it.assignment_id}`}>
                      {it.title}
                    </Link>
                  ) : (
                    <span>{it.title}</span>
                  )}
                  {it.kind === "assignment" && <ItemAssignmentSub course={course} item={it} />}
                </span>
                {teacherMode && (
                  <span className="row-actions">
                    <button
                      className="btn small"
                      onClick={() => setEditingItem({ moduleId: m.id, item: it })}
                    >
                      Edit
                    </button>
                    <button className="btn small" onClick={() => removeItem(it.id)}>
                      Delete
                    </button>
                  </span>
                )}
              </div>
            ))}
        </div>
        );
      })}

      {editingModule && (
        <ModuleEditModal
          courseId={course.id}
          module={editingModule === "new" ? null : editingModule}
          nextPosition={course.modules.length}
          onClose={() => setEditingModule(null)}
          onSaved={() => {
            setEditingModule(null);
            reload();
          }}
        />
      )}
      {editingItem && (
        <ModuleItemEditModal
          moduleId={editingItem.moduleId}
          item={editingItem.item === "new" ? null : editingItem.item}
          nextPosition={
            course.modules.find((m) => m.id === editingItem.moduleId)?.items.length ?? 0
          }
          assignments={course.assignments}
          onClose={() => setEditingItem(null)}
          onSaved={() => {
            setEditingItem(null);
            reload();
          }}
        />
      )}
    </CourseLayout>
  );
}

function ItemAssignmentSub({ course, item }: { course: CourseDetail; item: ModuleItem }) {
  const a = course.assignments.find((x) => x.id === item.assignment_id);
  if (!a) return null;
  return (
    <div className="mi-sub">
      {a.due_at ? `${new Date(a.due_at).toLocaleDateString()} · ` : ""}
      {a.points_possible} pts
    </div>
  );
}
