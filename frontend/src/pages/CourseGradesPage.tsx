import { Fragment, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Gradebook } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseGradesPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  const { user } = useAuth();
  const [gb, setGb] = useState<Gradebook | null>(null);
  const [onlyGraded, setOnlyGraded] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (courseId) api.getGradebook(courseId, onlyGraded).then(setGb);
  }, [courseId, onlyGraded]);

  if (!course || !gb) return <Spinner />;
  const pct = gb.total_percentage;

  return (
    <CourseLayout course={course} section="Grades">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Grades for {user?.display_name ?? "you"}</h1>
        <button className="btn" onClick={() => window.print()}>
          🖨 Print Grades
        </button>
      </div>
      <div className="page-with-sidebar">
        <div className="col-main">
          <table className="data">
            <thead>
              <tr>
                <th>Name</th>
                <th>Due</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {gb.rows.map((r) => (
                <Fragment key={r.assignment_id}>
                  <tr>
                    <td>
                      <Link to={`/courses/${course.id}/assignments/${r.assignment_id}`}>
                        {r.title}
                      </Link>
                      <div className="muted" style={{ fontSize: 12 }}>
                        {r.group_name}
                      </div>
                    </td>
                    <td>{r.due_at ? new Date(r.due_at).toLocaleString() : ""}</td>
                    <td>{r.submitted_at ? new Date(r.submitted_at).toLocaleString() : ""}</td>
                    <td>
                      {r.status === "missing" && (
                        <span className="badge-pill missing">missing</span>
                      )}
                      {r.status === "late" && <span className="badge-pill late">late</span>}
                    </td>
                    <td>
                      {r.score != null ? `${r.score} / ${r.points_possible}` : `⊘ / ${r.points_possible}`}
                    </td>
                  </tr>
                  {showDetails && (r.feedback_md || r.rubric_breakdown.length > 0) && (
                    <tr>
                      <td colSpan={5} style={{ background: "#fafafa" }}>
                        {r.rubric_breakdown.length > 0 && (
                          <table className="data" style={{ marginBottom: 8 }}>
                            <tbody>
                              {r.rubric_breakdown.map((rb, i) => (
                                <tr key={i}>
                                  <td>{rb.criterion}</td>
                                  <td>
                                    {rb.points_awarded}/{rb.points_possible}
                                  </td>
                                  <td>{rb.note}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                        {r.feedback_md && <Markdown>{r.feedback_md}</Markdown>}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {gb.groups.map((g) => (
                <tr key={"g-" + g.name} style={{ fontWeight: 700 }}>
                  <td colSpan={3}>{g.name}</td>
                  <td>{g.percentage != null ? `${g.percentage.toFixed(1)}%` : "N/A"}</td>
                  <td>
                    {g.earned.toFixed(2)} / {g.possible.toFixed(2)}
                  </td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700, fontSize: 18 }}>
                <td colSpan={4}>Total</td>
                <td>{pct != null ? `${pct.toFixed(2)}%` : "N/A"}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="col-side">
          <div className="widget">
            <h2>Total: {pct != null ? `${pct.toFixed(0)}%` : "N/A"}</h2>
            <button className="btn small" onClick={() => setShowDetails(!showDetails)}>
              {showDetails ? "Hide" : "Show"} all details
            </button>
          </div>
          {gb.groups.some((g) => g.weight != null) && (
            <div className="widget">
              <strong>Assignments are weighted by group:</strong>
              <table className="data" style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>Group</th>
                    <th>Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {gb.groups.map((g) => (
                    <tr key={g.name}>
                      <td>{g.name}</td>
                      <td>{g.weight != null ? `${g.weight}%` : "—"}</td>
                    </tr>
                  ))}
                  <tr style={{ fontWeight: 700 }}>
                    <td>Total</td>
                    <td>{gb.groups.reduce((s, g) => s + (g.weight ?? 0), 0)}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          <div className="widget">
            <label>
              <input
                type="checkbox"
                checked={onlyGraded}
                onChange={(e) => setOnlyGraded(e.target.checked)}
              />{" "}
              Calculate based only on graded assignments
            </label>
            <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              The total above reflects only assignments that have a grade. Editable "what-if" scores
              are not supported.
            </p>
          </div>
        </div>
      </div>
    </CourseLayout>
  );
}
