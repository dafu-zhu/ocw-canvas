import { useState } from "react";
import { api } from "../../api/client";
import type { Course } from "../../api/types";
import { Modal } from "../Modal";

export function CourseEditModal({
  course,
  onClose,
  onSaved,
}: {
  course: Course | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [f, setF] = useState<Partial<Course>>(
    course ?? { code: "", title: "", color: "#394B58", status: "active", display_order: 0 },
  );
  const [busy, setBusy] = useState(false);
  function up<K extends keyof Course>(k: K, v: Course[K]) {
    setF((s) => ({ ...s, [k]: v }));
  }
  async function save() {
    setBusy(true);
    try {
      if (course) await api.updateCourse(course.id, f);
      else await api.createCourse(f);
      onSaved();
    } finally {
      setBusy(false);
    }
  }
  async function del() {
    if (!course || !confirm("Delete this course and everything in it?")) return;
    await api.deleteCourse(course.id);
    onSaved();
  }
  return (
    <Modal
      title={course ? "Edit course" : "Add course"}
      onClose={onClose}
      footer={
        <>
          {course ? (
            <button className="btn" onClick={del}>
              Delete course
            </button>
          ) : (
            <span />
          )}
          <span>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button
              className="btn primary"
              style={{ marginLeft: 8 }}
              disabled={busy}
              onClick={save}
            >
              Save
            </button>
          </span>
        </>
      }
    >
      <label className="req">Code</label>
      <input value={f.code ?? ""} onChange={(e) => up("code", e.target.value)} placeholder="MIT 18.100B" />
      <label className="req">Title</label>
      <input value={f.title ?? ""} onChange={(e) => up("title", e.target.value)} placeholder="Real Analysis" />
      <label>Institution</label>
      <input
        value={f.institution ?? ""}
        onChange={(e) => up("institution", e.target.value)}
        placeholder="MIT OpenCourseWare"
      />
      <label>Term label</label>
      <input
        value={f.term_label ?? ""}
        onChange={(e) => up("term_label", e.target.value)}
        placeholder="Spring 2025"
      />
      <label>Instructor</label>
      <input value={f.instructor ?? ""} onChange={(e) => up("instructor", e.target.value)} />
      <label>Official course URL</label>
      <input
        value={f.external_home_url ?? ""}
        onChange={(e) => up("external_home_url", e.target.value)}
        placeholder="https://ocw.mit.edu/..."
      />
      <label>Textbook</label>
      <input value={f.textbook ?? ""} onChange={(e) => up("textbook", e.target.value)} />
      <label>Home page (markdown)</label>
      <textarea rows={5} value={f.home_page_md ?? ""} onChange={(e) => up("home_page_md", e.target.value)} />
      <label>Syllabus (markdown)</label>
      <textarea rows={6} value={f.syllabus_md ?? ""} onChange={(e) => up("syllabus_md", e.target.value)} />
      <label>Description (card blurb)</label>
      <input value={f.description ?? ""} onChange={(e) => up("description", e.target.value)} />
      <label>Card color (hex)</label>
      <input value={f.color ?? ""} onChange={(e) => up("color", e.target.value)} placeholder="#8B0000" />
      <label>Status</label>
      <select
        value={f.status ?? "active"}
        onChange={(e) => up("status", e.target.value as Course["status"])}
      >
        <option value="active">active</option>
        <option value="completed">completed</option>
        <option value="planned">planned</option>
      </select>
      <label>Display order</label>
      <input
        type="number"
        value={f.display_order ?? 0}
        onChange={(e) => up("display_order", Number(e.target.value))}
      />
    </Modal>
  );
}
