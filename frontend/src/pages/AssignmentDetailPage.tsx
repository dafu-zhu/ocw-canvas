import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiBase } from "../api/client";
import type { AssignmentDetail, SolutionInfo } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function AssignmentDetailPage() {
  const { courseId, assignmentId } = useParams();
  const { course } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [a, setA] = useState<AssignmentDetail | null>(null);
  const [info, setInfo] = useState<SolutionInfo | null>(null);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [showRef, setShowRef] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function reloadA() {
    if (!assignmentId) return;
    api.getAssignment(assignmentId).then(setA);
    api.getSolution(assignmentId).then(setInfo);
  }
  useEffect(reloadA, [assignmentId]);

  if (!course || !a || !info) return <Spinner />;
  const latest = a.submissions[a.submissions.length - 1];
  const noKey = info.key_kind === "none";

  async function submit() {
    setBusy(true);
    try {
      await api.submit(a!.id, { text: text || undefined, files });
      setText("");
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      reloadA();
    } finally {
      setBusy(false);
    }
  }

  async function generateSolution() {
    setGenBusy(true);
    try {
      await api.generateSolution(a!.id);
      reloadA();
    } finally {
      setGenBusy(false);
    }
  }

  return (
    <CourseLayout course={course} section="Assignments">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">{a.title}</h1>
          {a.due_at && <div className="muted">Due: {new Date(a.due_at).toLocaleString()}</div>}
        </div>
        <div style={{ fontSize: 22, fontWeight: 300 }}>{a.points_possible} Points Possible</div>
      </div>

      <details open style={{ margin: "16px 0" }}>
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Details</summary>
        <div style={{ marginTop: 8 }}>
          {a.description_md ? (
            <Markdown>{a.description_md}</Markdown>
          ) : (
            <span className="muted">No description.</span>
          )}
        </div>
      </details>

      {/* Submit panel */}
      <h2 style={{ fontWeight: 400 }}>
        {latest && latest.status === "graded" ? "Resubmit" : "Submit"}
      </h2>
      {noKey && (
        <div className="muted" style={{ marginBottom: 8, fontSize: 13 }}>
          No solution key yet — your submission will be recorded and graded once a key is attached
          {info.generation_available ? " or the AI solution is generated" : ""}.
        </div>
      )}
      {a.accepts_text && (
        <>
          <label className="muted">Text / LaTeX</label>
          <textarea
            rows={4}
            style={{ width: "100%" }}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </>
      )}
      {a.accepts_files && (
        <div style={{ margin: "10px 0" }}>
          <input
            ref={fileRef}
            type="file"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
        </div>
      )}
      <button
        className="btn primary"
        disabled={busy || (!text && files.length === 0)}
        onClick={submit}
      >
        {busy ? "Submitting…" : "Submit Assignment"}
      </button>

      {/* Submission history */}
      {a.submissions.length > 0 && (
        <>
          <h2 style={{ fontWeight: 400, marginTop: 24 }}>Submissions</h2>
          {a.submissions.map((s) => (
            <div className="module" key={s.id}>
              <div className="module-head">
                Attempt {s.attempt_number}
                {s.is_late && (
                  <span className="badge-pill late" style={{ marginLeft: 8 }}>
                    late
                  </span>
                )}
                <span style={{ marginLeft: 8 }} className="muted">
                  {s.submitted_at && new Date(s.submitted_at).toLocaleString()}
                </span>
              </div>
              <div className="module-item">
                <div style={{ flex: 1 }}>
                  {s.text_body && <Markdown>{s.text_body}</Markdown>}
                  {s.file_paths.map((p) => (
                    <div key={p}>
                      <a
                        href={`${apiBase}/api/files/submissions/${p}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {p.split("/").pop()}
                      </a>
                    </div>
                  ))}
                  {s.grade ? (
                    <div style={{ marginTop: 10 }}>
                      <strong>
                        Score: {s.grade.final_score} / {s.grade.score_out_of}
                      </strong>
                      {s.grade.late_penalty_applied > 0 && (
                        <span className="muted"> (late penalty −{s.grade.late_penalty_applied})</span>
                      )}
                      <span className="muted" style={{ marginLeft: 8 }}>
                        graded by {s.grade.graded_by}
                        {s.grade.model ? ` (${s.grade.model})` : ""}
                      </span>
                      {s.grade.rubric_breakdown.length > 0 && (
                        <table className="data" style={{ marginTop: 8 }}>
                          <thead>
                            <tr>
                              <th>Criterion</th>
                              <th>Awarded</th>
                              <th>Out of</th>
                              <th>Note</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s.grade.rubric_breakdown.map((r, i) => (
                              <tr key={i}>
                                <td>{r.criterion}</td>
                                <td>{r.points_awarded}</td>
                                <td>{r.points_possible}</td>
                                <td>{r.note}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                      {s.grade.feedback_md && (
                        <div style={{ marginTop: 8 }}>
                          <Markdown>{s.grade.feedback_md}</Markdown>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="muted" style={{ marginTop: 8 }}>
                      {s.status === "submitted"
                        ? noKey
                          ? "Submitted — awaiting a solution key before autograding."
                          : "Submitted — not yet graded."
                        : s.status === "grading"
                          ? "Grading…"
                          : s.status === "grading_failed"
                            ? "Grading failed."
                            : s.status}
                    </div>
                  )}
                  {teacherMode && (
                    <SubmissionTeacherActions
                      submissionId={s.id}
                      hasKey={!noKey}
                      onChanged={reloadA}
                    />
                  )}
                </div>
              </div>
            </div>
          ))}
        </>
      )}

      {/* Reference solution — hidden for project-mode assignments (AI grades without a key) */}
      {a.requires_solution_key && (
      <div style={{ marginTop: 24 }}>
        <button className="btn" onClick={() => setShowRef(!showRef)}>
          {showRef ? "Hide" : "View"} reference solution
        </button>
        {teacherMode && info.ai_solution?.status !== "ready" && (
          <button
            className="btn"
            style={{ marginLeft: 8 }}
            disabled={genBusy || !info.generation_available}
            onClick={generateSolution}
            title={
              info.generation_available
                ? ""
                : "AI solution generation is disabled (no credential / flag off)"
            }
          >
            {genBusy ? "Generating…" : "Generate AI solution"}
          </button>
        )}
        {showRef && (
          <div style={{ marginTop: 10 }}>
            {info.official_solution_url ? (
              <a
                href={info.official_solution_url}
                target="_blank"
                rel="noreferrer"
                className="external-arrow"
              >
                Official solution
              </a>
            ) : info.ai_solution?.status === "ready" ? (
              <Markdown>{info.ai_solution.content_md}</Markdown>
            ) : info.ai_solution?.status === "generating" ? (
              <span className="muted">Generating the reference solution…</span>
            ) : info.ai_solution?.status === "failed" ? (
              <span className="muted">
                Solution generation failed: {info.ai_solution.error}
                {teacherMode && info.generation_available && (
                  <button
                    className="btn small"
                    style={{ marginLeft: 8 }}
                    disabled={genBusy}
                    onClick={generateSolution}
                  >
                    Retry
                  </button>
                )}
              </span>
            ) : (
              <span className="muted">
                No solution available yet
                {info.generation_available ? " — generate it above" : ""}.
              </span>
            )}
          </div>
        )}
      </div>
      )}
    </CourseLayout>
  );
}

function SubmissionTeacherActions({
  submissionId,
  hasKey,
  onChanged,
}: {
  submissionId: string;
  hasKey: boolean;
  onChanged: () => void;
}) {
  const [score, setScore] = useState("");
  const [fb, setFb] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 10 }}>
      <strong>Teacher</strong>
      <div style={{ display: "flex", gap: 8, marginTop: 6, alignItems: "center", flexWrap: "wrap" }}>
        <input
          style={{ width: 80 }}
          placeholder="score"
          value={score}
          onChange={(e) => setScore(e.target.value)}
        />
        <input
          style={{ flex: 1, minWidth: 160 }}
          placeholder="feedback (markdown)"
          value={fb}
          onChange={(e) => setFb(e.target.value)}
        />
        <button
          className="btn small"
          disabled={busy || score === ""}
          onClick={async () => {
            setBusy(true);
            try {
              await api.manualGrade(submissionId, Number(score), fb);
              onChanged();
            } finally {
              setBusy(false);
            }
          }}
        >
          Save manual grade
        </button>
        <button
          className="btn small primary"
          disabled={busy || !hasKey}
          title={hasKey ? "" : "no solution key — attach one or generate the AI solution first"}
          onClick={async () => {
            setBusy(true);
            try {
              await api.regrade(submissionId);
              onChanged();
            } catch (e) {
              alert(String(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          Re-grade with AI
        </button>
      </div>
    </div>
  );
}
