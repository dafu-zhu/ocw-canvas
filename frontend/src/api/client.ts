import type {
  AssignmentGroup,
  Course,
  CourseDetail,
  Module,
  ModuleItem,
  User,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) throw new ApiError(res.status, (data && data.detail) || res.statusText);
  return data as T;
}

export const api = {
  // auth
  login: (email: string, password: string) => req<User>("POST", "/auth/login", { email, password }),
  logout: () => req<{ ok: boolean }>("POST", "/auth/logout"),
  me: () => req<User>("GET", "/auth/me"),

  // courses
  listCourses: () => req<Course[]>("GET", "/courses"),
  getCourse: (id: string) => req<CourseDetail>("GET", `/courses/${id}`),
  createCourse: (c: Partial<Course>) => req<Course>("POST", "/courses", c),
  updateCourse: (id: string, c: Partial<Course>) => req<Course>("PUT", `/courses/${id}`, c),
  deleteCourse: (id: string) => req<void>("DELETE", `/courses/${id}`),

  // modules
  createModule: (courseId: string, m: { title: string; position: number; published?: boolean }) =>
    req<Module>("POST", `/courses/${courseId}/modules`, m),
  updateModule: (id: string, m: { title: string; position: number; published?: boolean }) =>
    req<Module>("PUT", `/modules/${id}`, m),
  deleteModule: (id: string) => req<void>("DELETE", `/modules/${id}`),

  // module items
  createItem: (moduleId: string, it: Partial<ModuleItem> & { kind: string; title: string }) =>
    req<ModuleItem>("POST", `/modules/${moduleId}/items`, it),
  updateItem: (id: string, it: Partial<ModuleItem> & { kind: string; title: string }) =>
    req<ModuleItem>("PUT", `/module-items/${id}`, it),
  deleteItem: (id: string) => req<void>("DELETE", `/module-items/${id}`),

  // assignment groups
  createGroup: (courseId: string, g: Partial<AssignmentGroup> & { name: string }) =>
    req<AssignmentGroup>("POST", `/courses/${courseId}/assignment-groups`, g),
  updateGroup: (id: string, g: Partial<AssignmentGroup> & { name: string }) =>
    req<AssignmentGroup>("PUT", `/assignment-groups/${id}`, g),
  deleteGroup: (id: string) => req<void>("DELETE", `/assignment-groups/${id}`),
};
