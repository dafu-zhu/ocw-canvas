import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { CourseDetail } from "../api/types";

export function useCourse(courseId: string | undefined) {
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    if (!courseId) return;
    api
      .getCourse(courseId)
      .then(setCourse)
      .catch((e) => setError(String(e)));
  }, [courseId]);
  useEffect(reload, [reload]);
  return { course, error, reload };
}
