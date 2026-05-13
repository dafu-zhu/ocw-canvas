import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type { CourseDetail } from "../api/types";
import { AppLayout } from "./AppLayout";

const NAV: { to: string; label: string }[] = [
  { to: "", label: "Home" },
  { to: "/syllabus", label: "Syllabus" },
  { to: "/modules", label: "Modules" },
  { to: "/assignments", label: "Assignments" },
  { to: "/grades", label: "Grades" },
  { to: "/videos", label: "Video Lectures" },
  { to: "/announcements", label: "Announcements" },
];

export function CourseLayout({
  course,
  section,
  children,
  sidebar,
}: {
  course: CourseDetail;
  section: string; // breadcrumb leaf label
  children: ReactNode;
  sidebar?: ReactNode;
}) {
  const base = `/courses/${course.id}`;
  const crumbs =
    section === "Home"
      ? [{ label: `${course.code} ${course.title}` }]
      : [{ label: `${course.code} ${course.title}`, to: base }, { label: section }];

  return (
    <AppLayout crumbs={crumbs}>
      <div className="content-wrap">
        <nav className="course-nav">
          <div className="term">{course.term_label}</div>
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={base + n.to}
              end={n.to === ""}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="content">
          {sidebar ? (
            <div className="page-with-sidebar">
              <div className="col-main">{children}</div>
              <div className="col-side">{sidebar}</div>
            </div>
          ) : (
            children
          )}
        </div>
      </div>
    </AppLayout>
  );
}
