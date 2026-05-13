import { useState } from "react";
import { api } from "../../api/client";
import type { AssignmentSummary, Module, ModuleItem, ModuleItemKind } from "../../api/types";
import { Modal } from "../Modal";

export function ModuleEditModal({
  courseId,
  module,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  module: Module | null;
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(module?.title ?? "");
  const [position, setPosition] = useState(module?.position ?? nextPosition);
  const [published, setPublished] = useState(module?.published ?? true);
  async function save() {
    if (module) await api.updateModule(module.id, { title, position, published });
    else await api.createModule(courseId, { title, position, published });
    onSaved();
  }
  return (
    <Modal
      title={module ? "Edit module" : "Add module"}
      onClose={onClose}
      footer={
        <span style={{ marginLeft: "auto" }}>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>
            Save
          </button>
        </span>
      }
    >
      <label className="req">Title</label>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Unit 1 — The Real Numbers"
      />
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

const KINDS: ModuleItemKind[] = ["link", "video", "assignment", "note", "header"];

export function ModuleItemEditModal({
  moduleId,
  item,
  nextPosition,
  assignments,
  onClose,
  onSaved,
}: {
  moduleId: string;
  item: ModuleItem | null;
  nextPosition: number;
  assignments: AssignmentSummary[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [kind, setKind] = useState<ModuleItemKind>(item?.kind ?? "link");
  const [title, setTitle] = useState(item?.title ?? "");
  const [externalUrl, setExternalUrl] = useState(item?.external_url ?? "");
  const [assignmentId, setAssignmentId] = useState<string>(item?.assignment_id ?? "");
  const [textMd, setTextMd] = useState(item?.text_md ?? "");
  const [indent, setIndent] = useState(item?.indent ?? 0);
  const [position, setPosition] = useState(item?.position ?? nextPosition);
  const [published, setPublished] = useState(item?.published ?? true);

  async function save() {
    const payload = {
      kind,
      title,
      external_url: kind === "link" || kind === "video" ? externalUrl : "",
      assignment_id: kind === "assignment" ? assignmentId || null : null,
      text_md: kind === "note" || kind === "header" ? textMd : "",
      indent,
      position,
      published,
    };
    if (item) await api.updateItem(item.id, payload);
    else await api.createItem(moduleId, payload);
    onSaved();
  }

  return (
    <Modal
      title={item ? "Edit module item" : "Add module item"}
      onClose={onClose}
      footer={
        <span style={{ marginLeft: "auto" }}>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>
            Save
          </button>
        </span>
      }
    >
      <label className="req">Kind</label>
      <select value={kind} onChange={(e) => setKind(e.target.value as ModuleItemKind)}>
        {KINDS.map((k) => (
          <option key={k} value={k}>
            {k}
          </option>
        ))}
      </select>
      <label className="req">Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} />
      {(kind === "link" || kind === "video") && (
        <>
          <label className="req">External URL (opens in a new tab — never re-host the file)</label>
          <input
            value={externalUrl}
            onChange={(e) => setExternalUrl(e.target.value)}
            placeholder="https://ocw.mit.edu/..."
          />
        </>
      )}
      {kind === "assignment" && (
        <>
          <label>Assignment</label>
          <select value={assignmentId} onChange={(e) => setAssignmentId(e.target.value)}>
            <option value="">(none — pick one)</option>
            {assignments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </>
      )}
      {(kind === "note" || kind === "header") && (
        <>
          <label>Text (markdown)</label>
          <textarea rows={4} value={textMd} onChange={(e) => setTextMd(e.target.value)} />
        </>
      )}
      <label>Indent (0–2)</label>
      <input
        type="number"
        min={0}
        max={2}
        value={indent}
        onChange={(e) => setIndent(Number(e.target.value))}
      />
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
