import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Assignment, AssignmentGroup, AssignmentSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { AssignmentEditModal } from "../components/edit/AssignmentEditModal";
import { AssignmentGroupEditModal } from "../components/edit/AssignmentGroupEditModal";
import { useCourse } from "../lib/useCourse";

type Mode = "date" | "type";

function dateBucket(
  a: AssignmentSummary,
): "Overdue Assignments" | "Upcoming Assignments" | "Undated Assignments" {
  if (!a.due_at) return "Undated Assignments";
  return new Date(a.due_at) < new Date() ? "Overdue Assignments" : "Upcoming Assignments";
}

export function CourseAssignmentsPage() {
  const { courseId } = useParams();
  const { course, reload } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [mode, setMode] = useState<Mode>("date");
  const [editing, setEditing] = useState<Assignment | "new" | null>(null);
  const [editingGroup, setEditingGroup] = useState<AssignmentGroup | "new" | null>(null);

  const grouped = useMemo(() => {
    const m = new Map<string, AssignmentSummary[]>();
    if (!course) return m;
    const byId = new Map<string, AssignmentGroup>(
      course.assignment_groups.map((g) => [g.id, g]),
    );
    for (const a of course.assignments) {
      const key =
        mode === "date"
          ? dateBucket(a)
          : a.assignment_group_id && byId.has(a.assignment_group_id)
            ? byId.get(a.assignment_group_id)!.name
            : "(ungrouped)";
      if (!m.has(key)) m.set(key, []);
      m.get(key)!.push(a);
    }
    return m;
  }, [course, mode]);

  if (!course) return <Spinner />;
  const order =
    mode === "date"
      ? ["Overdue Assignments", "Upcoming Assignments", "Undated Assignments"]
      : [...course.assignment_groups.map((g) => g.name), "(ungrouped)"];

  function openEdit(id: string) {
    api.getAssignment(id).then(setEditing);
  }

  return (
    <CourseLayout course={course} section="Assignments">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Assignments</h1>
        <div>
          <button
            className={"btn" + (mode === "date" ? " primary" : "")}
            onClick={() => setMode("date")}
          >
            Show by date
          </button>
          <button
            className={"btn" + (mode === "type" ? " primary" : "")}
            style={{ marginLeft: 6 }}
            onClick={() => setMode("type")}
          >
            Show by type
          </button>
          {teacherMode && (
            <button
              className="btn primary"
              style={{ marginLeft: 12 }}
              onClick={() => setEditing("new")}
            >
              + Assignment
            </button>
          )}
        </div>
      </div>

      {teacherMode && (
        <div className="widget" style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>Assignment groups</strong>
            <button className="btn small" onClick={() => setEditingGroup("new")}>
              + Add group
            </button>
          </div>
          {course.assignment_groups.length === 0 ? (
            <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>
              No groups yet.
            </div>
          ) : (
            <table className="data" style={{ marginTop: 8 }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Weight</th>
                  <th>Drop lowest</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {course.assignment_groups.map((g) => (
                  <tr key={g.id}>
                    <td>{g.name}</td>
                    <td>{g.weight != null ? `${g.weight}%` : "—"}</td>
                    <td>{g.drop_lowest_n}</td>
                    <td>
                      <button className="btn small" onClick={() => setEditingGroup(g)}>
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {course.assignments.length === 0 && (
        <div className="center-empty">No assignments yet.</div>
      )}
      {order
        .filter((k) => grouped.has(k))
        .map((k) => (
          <div className="module" key={k}>
            <div className="module-head">{k}</div>
            {grouped.get(k)!.map((a) => (
              <div className="module-item" key={a.id}>
                <span className="mi-icon">📝</span>
                <span style={{ flex: 1 }}>
                  <Link to={`/courses/${course.id}/assignments/${a.id}`}>{a.title}</Link>
                  <div className="mi-sub">
                    {a.due_at ? `Due ${new Date(a.due_at).toLocaleString()} | ` : ""}–/
                    {a.points_possible} pts
                  </div>
                </span>
                {teacherMode && (
                  <span className="row-actions">
                    <button className="btn small" onClick={() => openEdit(a.id)}>
                      Edit
                    </button>
                  </span>
                )}
              </div>
            ))}
          </div>
        ))}

      {editing && (
        <AssignmentEditModal
          courseId={course.id}
          assignment={editing === "new" ? null : editing}
          groups={course.assignment_groups}
          nextPosition={course.assignments.length}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
      {editingGroup && (
        <AssignmentGroupEditModal
          courseId={course.id}
          group={editingGroup === "new" ? null : editingGroup}
          nextPosition={course.assignment_groups.length}
          onClose={() => setEditingGroup(null)}
          onSaved={() => {
            setEditingGroup(null);
            reload();
          }}
        />
      )}
    </CourseLayout>
  );
}
