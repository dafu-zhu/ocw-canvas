import { Link } from "react-router-dom";
import type { CourseDetail } from "../api/types";
import { MiniCalendar } from "./MiniCalendar";

export function CourseSidebar({ course }: { course: CourseDetail }) {
  const eventDays = new Set(
    course.assignments.filter((a) => a.due_at).map((a) => a.due_at!.slice(0, 10)),
  );
  return (
    <>
      <div className="widget">
        <Link className="btn" to="/calendar" style={{ width: "100%", marginBottom: 8 }}>
          📊 View Course Stream
        </Link>
        <Link className="btn" to="/calendar" style={{ width: "100%", marginBottom: 8 }}>
          📅 View Course Calendar
        </Link>
        <span className="btn muted" style={{ width: "100%" }}>
          🔔 View Course Notifications
        </span>
      </div>
      <div className="widget">
        <h2>To Do</h2>
        <div className="muted" style={{ fontSize: 13 }}>
          Assignment deadlines for this course appear here.
        </div>
      </div>
      <div className="widget">
        <MiniCalendar eventDays={eventDays} />
      </div>
    </>
  );
}
