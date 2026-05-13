import type {
  AiSolution,
  Assignment,
  AssignmentDetail,
  AssignmentGroup,
  Course,
  CourseDetail,
  Grade,
  Gradebook,
  Module,
  ModuleItem,
  SolutionInfo,
  Submission,
  User,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export const apiBase = BASE;

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

async function reqForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, { method, credentials: "include", body: form });
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

  // assignments
  listAssignments: (courseId: string) =>
    req<Assignment[]>("GET", `/courses/${courseId}/assignments`),
  getAssignment: (id: string) => req<AssignmentDetail>("GET", `/assignments/${id}`),
  createAssignment: (courseId: string, a: Partial<Assignment> & { title: string }) =>
    req<Assignment>("POST", `/courses/${courseId}/assignments`, a),
  updateAssignment: (id: string, a: Partial<Assignment> & { title: string }) =>
    req<Assignment>("PUT", `/assignments/${id}`, a),
  deleteAssignment: (id: string) => req<void>("DELETE", `/assignments/${id}`),

  // submissions
  submit: (assignmentId: string, opts: { text?: string; files: File[] }) => {
    const fd = new FormData();
    if (opts.text) fd.append("text_body", opts.text);
    for (const f of opts.files) fd.append("files", f);
    return reqForm<Submission>("POST", `/assignments/${assignmentId}/submissions`, fd);
  },
  manualGrade: (submissionId: string, score: number, feedback: string) => {
    const fd = new FormData();
    fd.append("score", String(score));
    fd.append("feedback_md", feedback);
    return reqForm<Grade>("POST", `/submissions/${submissionId}/grade`, fd);
  },

  // gradebook
  getGradebook: (courseId: string, onlyGraded = true) =>
    req<Gradebook>("GET", `/courses/${courseId}/gradebook?only_graded=${onlyGraded}`),

  // AI
  getSolution: (assignmentId: string) =>
    req<SolutionInfo>("GET", `/assignments/${assignmentId}/solution`),
  generateSolution: (assignmentId: string) =>
    req<AiSolution>("POST", `/assignments/${assignmentId}/generate-solution`),
  regrade: (submissionId: string) => req<Grade>("POST", `/submissions/${submissionId}/regrade`),
};
