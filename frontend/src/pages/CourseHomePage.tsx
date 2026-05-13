import { useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { CourseSidebar } from "../components/CourseSidebar";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { CourseEditModal } from "../components/edit/CourseEditModal";
import { useCourse } from "../lib/useCourse";

export function CourseHomePage() {
  const { courseId } = useParams();
  const { teacherMode } = useAuth();
  const { course, reload } = useCourse(courseId);
  const [editing, setEditing] = useState(false);
  if (!course) return <Spinner />;
  return (
    <CourseLayout course={course} section="Home" sidebar={<CourseSidebar course={course} />}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <h1 className="page-title">
          {course.code} {course.term_label && `(${course.term_label})`} {course.title}
        </h1>
        {teacherMode && (
          <button className="btn small" onClick={() => setEditing(true)}>
            Edit course
          </button>
        )}
      </div>
      <p className="muted">{[course.institution, course.instructor].filter(Boolean).join(" · ")}</p>
      {course.home_page_md ? (
        <Markdown>{course.home_page_md}</Markdown>
      ) : (
        <p className="muted">No front page content yet.</p>
      )}
      {course.external_home_url && (
        <p style={{ marginTop: 16 }}>
          <a
            href={course.external_home_url}
            target="_blank"
            rel="noreferrer"
            className="external-arrow"
          >
            Official course site
          </a>
        </p>
      )}
      {editing && (
        <CourseEditModal
          course={course}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
        />
      )}
    </CourseLayout>
  );
}
