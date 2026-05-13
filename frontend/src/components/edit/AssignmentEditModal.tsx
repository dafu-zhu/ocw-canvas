import { useState } from "react";
import { api } from "../../api/client";
import type { Assignment, AssignmentGroup, LatePolicy } from "../../api/types";
import { Modal } from "../Modal";

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function fromLocalInput(v: string): string | null {
  return v ? new Date(v).toISOString() : null;
}

export function AssignmentEditModal({
  courseId,
  assignment,
  groups,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  assignment: Assignment | null;
  groups: AssignmentGroup[];
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(assignment?.title ?? "");
  const [groupId, setGroupId] = useState(assignment?.assignment_group_id ?? "");
  const [desc, setDesc] = useState(assignment?.description_md ?? "");
  const [points, setPoints] = useState(assignment?.points_possible ?? 100);
  const [due, setDue] = useState(toLocalInput(assignment?.due_at ?? null));
  const [acceptsFiles, setAcceptsFiles] = useState(assignment?.accepts_files ?? true);
  const [acceptsText, setAcceptsText] = useState(assignment?.accepts_text ?? true);
  const [solUrl, setSolUrl] = useState(assignment?.official_solution_url ?? "");
  const [latePolicy, setLatePolicy] = useState<LatePolicy>(assignment?.late_policy ?? "flag_only");
  const [lateValue, setLateValue] = useState<string>(
    assignment?.late_value != null ? String(assignment.late_value) : "",
  );
  const [position, setPosition] = useState(assignment?.position ?? nextPosition);
  const [published, setPublished] = useState(assignment?.published ?? true);

  async function save() {
    const payload = {
      title,
      assignment_group_id: groupId || null,
      description_md: desc,
      points_possible: points,
      due_at: fromLocalInput(due),
      accepts_files: acceptsFiles,
      accepts_text: acceptsText,
      official_solution_url: solUrl,
      late_policy: latePolicy,
      late_value: lateValue === "" ? null : Number(lateValue),
      position,
      published,
    };
    if (assignment) await api.updateAssignment(assignment.id, payload);
    else await api.createAssignment(courseId, payload);
    onSaved();
  }
  async function del() {
    if (!assignment || !confirm("Delete this assignment and its submissions?")) return;
    await api.deleteAssignment(assignment.id);
    onSaved();
  }

  return (
    <Modal
      title={assignment ? "Edit assignment" : "Add assignment"}
      onClose={onClose}
      footer={
        <>
          {assignment ? (
            <button className="btn" onClick={del}>
              Delete
            </button>
          ) : (
            <span />
          )}
          <span style={{ marginLeft: "auto" }}>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>
              Save
            </button>
          </span>
        </>
      }
    >
      <label className="req">Title</label>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Problem Set 1 — Sequences"
      />
      <label>Assignment group</label>
      <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
        <option value="">(ungrouped)</option>
        {groups.map((g) => (
          <option key={g.id} value={g.id}>
            {g.name}
            {g.weight != null ? ` (${g.weight}%)` : ""}
          </option>
        ))}
      </select>
      <label>Description (markdown — put the link to the source problem-set PDF here)</label>
      <textarea rows={5} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <label>Points possible</label>
      <input type="number" value={points} onChange={(e) => setPoints(Number(e.target.value))} />
      <label>Due (local time)</label>
      <input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />
      <label>
        <input
          type="checkbox"
          checked={acceptsFiles}
          onChange={(e) => setAcceptsFiles(e.target.checked)}
        />{" "}
        Accept file uploads
      </label>
      <label>
        <input
          type="checkbox"
          checked={acceptsText}
          onChange={(e) => setAcceptsText(e.target.checked)}
        />{" "}
        Accept text / LaTeX entry
      </label>
      <label>Official solution URL (optional — if set, this is the answer key)</label>
      <input value={solUrl} onChange={(e) => setSolUrl(e.target.value)} />
      <label>Late policy</label>
      <select value={latePolicy} onChange={(e) => setLatePolicy(e.target.value as LatePolicy)}>
        <option value="none">none</option>
        <option value="flag_only">flag only</option>
        <option value="percent_per_day">percent per day</option>
      </select>
      {latePolicy === "percent_per_day" && (
        <>
          <label>% off per day late</label>
          <input
            value={lateValue}
            onChange={(e) => setLateValue(e.target.value)}
            placeholder="10"
          />
        </>
      )}
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
      <label>
        <input
          type="checkbox"
          checked={published}
          onChange={(e) => setPublished(e.target.checked)}
        />{" "}
        Published
      </label>
    </Modal>
  );
}
