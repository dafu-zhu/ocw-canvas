import { Link } from "react-router-dom";
import type { CourseDetail } from "../api/types";
import { MiniCalendar } from "./MiniCalendar";
import { TodoList } from "./TodoList";

export function CourseSidebar({ course }: { course: CourseDetail }) {
  const eventDays = new Set(
    course.assignments.filter((a) => a.due_at).map((a) => a.due_at!.slice(0, 10)),
  );
  const entries = course.assignments
    .filter((a) => a.due_at && new Date(a.due_at) > new Date())
    .sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime())
    .slice(0, 5)
    .map((a) => ({
      key: a.id,
      title: a.title,
      to: `/courses/${course.id}/assignments/${a.id}`,
      points: a.points_possible,
      dueAt: a.due_at,
    }));
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
        <TodoList entries={entries} empty="Nothing due. You're all caught up." />
      </div>
      <div className="widget">
        <MiniCalendar eventDays={eventDays} />
      </div>
    </>
  );
}
