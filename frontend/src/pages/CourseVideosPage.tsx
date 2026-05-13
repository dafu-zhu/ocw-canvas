import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseVideosPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  const videos = course.modules.flatMap((m) =>
    m.items.filter((it) => it.kind === "video").map((it) => ({ module: m.title, ...it })),
  );
  return (
    <CourseLayout course={course} section="Video Lectures">
      <h1 className="page-title">Video Lectures</h1>
      {videos.length === 0 && <div className="center-empty">No video lectures yet.</div>}
      {videos.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Module</th>
              <th>Lecture</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v) => (
              <tr key={v.id}>
                <td className="muted">{v.module}</td>
                <td>
                  <a href={v.external_url} target="_blank" rel="noreferrer" className="external-arrow">
                    {v.title}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </CourseLayout>
  );
}
