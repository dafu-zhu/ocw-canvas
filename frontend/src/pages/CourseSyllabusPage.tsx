import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { CourseSidebar } from "../components/CourseSidebar";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseSyllabusPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  const summary = [...course.assignments].sort((a, b) =>
    (a.due_at || "").localeCompare(b.due_at || ""),
  );
  return (
    <CourseLayout course={course} section="Syllabus" sidebar={<CourseSidebar course={course} />}>
      <h1 className="page-title">Syllabus</h1>
      {course.syllabus_md ? (
        <Markdown>{course.syllabus_md}</Markdown>
      ) : (
        <p className="muted">No syllabus text yet.</p>
      )}
      <h2 style={{ marginTop: 28, fontWeight: 400 }}>Course Summary</h2>
      <table className="data">
        <thead>
          <tr>
            <th>Date</th>
            <th>Assignment</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {summary.length === 0 && (
            <tr>
              <td colSpan={3} className="muted">
                No assignments yet.
              </td>
            </tr>
          )}
          {summary.map((a) => (
            <tr key={a.id}>
              <td>{a.due_at ? new Date(a.due_at).toLocaleDateString() : "—"}</td>
              <td>{a.title}</td>
              <td>{a.points_possible}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CourseLayout>
  );
}
