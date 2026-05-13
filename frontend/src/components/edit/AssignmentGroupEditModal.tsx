import { useState } from "react";
import { api } from "../../api/client";
import type { AssignmentGroup } from "../../api/types";
import { Modal } from "../Modal";

export function AssignmentGroupEditModal({
  courseId,
  group,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  group: AssignmentGroup | null;
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(group?.name ?? "");
  const [weight, setWeight] = useState<string>(group?.weight != null ? String(group.weight) : "");
  const [dropLowest, setDropLowest] = useState(group?.drop_lowest_n ?? 0);
  const [position, setPosition] = useState(group?.position ?? nextPosition);
  async function save() {
    const payload = {
      name,
      weight: weight === "" ? null : Number(weight),
      drop_lowest_n: dropLowest,
      position,
    };
    if (group) await api.updateGroup(group.id, payload);
    else await api.createGroup(courseId, payload);
    onSaved();
  }
  return (
    <Modal
      title={group ? "Edit assignment group" : "Add assignment group"}
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
      <label className="req">Name</label>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Problem Sets" />
      <label>Weight (% of course grade — leave blank for unweighted)</label>
      <input value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="50" />
      <label>Drop lowest N</label>
      <input
        type="number"
        min={0}
        value={dropLowest}
        onChange={(e) => setDropLowest(Number(e.target.value))}
      />
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
    </Modal>
  );
}
