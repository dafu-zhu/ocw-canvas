import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { AppLayout } from "../components/AppLayout";
import { Spinner } from "../components/Spinner";

export function CoursesListPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  useEffect(() => {
    api.listCourses().then(setCourses);
  }, []);
  return (
    <AppLayout crumbs={[{ label: "Courses" }]}>
      <div className="content">
        <h1 className="page-title">All Courses</h1>
        {courses === null ? (
          <Spinner />
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>Course</th>
                <th>Term</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/courses/${c.id}`}>
                      {c.code} — {c.title}
                    </Link>
                  </td>
                  <td className="muted">{c.term_label}</td>
                  <td className="muted">{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  );
}
