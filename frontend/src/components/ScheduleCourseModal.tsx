import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ScheduleResponse } from "../api/types";
import { Modal } from "./Modal";

function today(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function ScheduleCourseModal({
  courseId,
  defaultStartDate,
  onClose,
  onApplied,
}: {
  courseId: string;
  defaultStartDate?: string;
  onClose: () => void;
  onApplied: (resp: ScheduleResponse) => void;
}) {
  const [startDate, setStartDate] = useState(defaultStartDate ?? today());
  const [lecD, setLecD] = useState(3);
  const [hwD, setHwD] = useState(14);
  const [bufferD, setBufferD] = useState(7);
  const [preview, setPreview] = useState<ScheduleResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refreshPreview() {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.scheduleCourse(courseId, {
        start_date: startDate,
        lecture_cadence_days: lecD,
        homework_cadence_days: hwD,
        buffer_after_last_lecture_days: bufferD,
        apply: false,
      });
      setPreview(r);
    } catch (e) {
      setErr(String(e));
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  async function apply(activate: boolean) {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.scheduleCourse(courseId, {
        start_date: startDate,
        lecture_cadence_days: lecD,
        homework_cadence_days: hwD,
        buffer_after_last_lecture_days: bufferD,
        apply: true,
        activate,
      });
      onApplied(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Schedule course"
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button className="btn" disabled={busy} onClick={() => apply(false)}>
              Apply dates (keep planned)
            </button>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() => apply(true)}
              title="Set due dates and flip course.status to active"
            >
              Apply & activate
            </button>
          </span>
        </>
      }
    >
      <p className="muted" style={{ marginTop: 0 }}>
        Generates a deadline for every assignment using the rule:{" "}
        <em>due the day before the next lecture that's not covered by this homework</em>.
        Assignments without lecture coverage fall back to the homework cadence.
      </p>

      <label className="req">Start date (Lecture 1)</label>
      <input
        type="date"
        value={startDate}
        onChange={(e) => setStartDate(e.target.value)}
        onBlur={refreshPreview}
      />

      <div style={{ display: "flex", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <label>Days between lectures</label>
          <input
            type="number"
            min={1}
            value={lecD}
            onChange={(e) => setLecD(Math.max(1, Number(e.target.value)))}
            onBlur={refreshPreview}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label>Days between homework (fallback)</label>
          <input
            type="number"
            min={1}
            value={hwD}
            onChange={(e) => setHwD(Math.max(1, Number(e.target.value)))}
            onBlur={refreshPreview}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label>Buffer after last lecture (days)</label>
          <input
            type="number"
            min={0}
            value={bufferD}
            onChange={(e) => setBufferD(Math.max(0, Number(e.target.value)))}
            onBlur={refreshPreview}
          />
        </div>
      </div>

      {err && <div className="err">{err}</div>}

      {preview && (
        <>
          <h2 style={{ fontSize: 16, marginTop: 16, marginBottom: 6 }}>
            Proposed schedule ({preview.rows.length} assignments · {preview.num_lectures} lectures)
          </h2>
          <table className="data" style={{ marginTop: 4 }}>
            <thead>
              <tr>
                <th>Assignment</th>
                <th>Covers lectures</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((r) => (
                <tr key={r.assignment_id}>
                  <td>{r.title}</td>
                  <td>
                    {r.covers_lecture_from && r.covers_lecture_to
                      ? `${r.covers_lecture_from}–${r.covers_lecture_to}`
                      : "—"}
                  </td>
                  <td>{new Date(r.due_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Modal>
  );
}
