import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { AppLayout } from "../components/AppLayout";
import { MiniCalendar } from "../components/MiniCalendar";
import { Spinner } from "../components/Spinner";

export function CalendarPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [days, setDays] = useState<Set<string>>(new Set());
  useEffect(() => {
    api.listCourses().then(async (cs) => {
      setCourses(cs);
      const ds = new Set<string>();
      for (const c of cs) {
        const d = await api.getCourse(c.id);
        d.assignments.forEach((a) => a.due_at && ds.add(a.due_at.slice(0, 10)));
      }
      setDays(ds);
    });
  }, []);
  return (
    <AppLayout crumbs={[{ label: "Calendar" }]}>
      <div className="content">
        <h1 className="page-title">Calendar</h1>
        {courses === null ? (
          <Spinner />
        ) : (
          <div style={{ maxWidth: 420 }}>
            <MiniCalendar eventDays={days} />
          </div>
        )}
        <p className="muted" style={{ marginTop: 12 }}>
          Days with assignment deadlines are highlighted. Full agenda view is a later enhancement.
        </p>
      </div>
    </AppLayout>
  );
}
