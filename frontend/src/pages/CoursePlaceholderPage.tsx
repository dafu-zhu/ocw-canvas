import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

// Stand-in for course sections that arrive in a later phase (Assignments, Grades).
export function CoursePlaceholderPage({ section }: { section: string }) {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  return (
    <CourseLayout course={course} section={section}>
      <h1 className="page-title">{section}</h1>
      <div className="center-empty">
        This section arrives in a later phase of OCW Canvas. Course materials live under{" "}
        <strong>Modules</strong> for now.
      </div>
    </CourseLayout>
  );
}
