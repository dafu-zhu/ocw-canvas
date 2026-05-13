export interface User {
  id: string;
  email: string;
  display_name: string;
}

export type CourseStatus = "active" | "completed" | "planned";
export type ModuleItemKind = "link" | "video" | "assignment" | "note" | "header";

export interface Course {
  id: string;
  code: string;
  title: string;
  institution: string;
  term_label: string;
  instructor: string;
  external_home_url: string;
  textbook: string;
  home_page_md: string;
  syllabus_md: string;
  description: string;
  color: string;
  status: CourseStatus;
  display_order: number;
}

export interface ModuleItem {
  id: string;
  module_id: string;
  position: number;
  indent: number;
  kind: ModuleItemKind;
  title: string;
  external_url: string;
  assignment_id: string | null;
  text_md: string;
  published: boolean;
}

export interface Module {
  id: string;
  course_id: string;
  title: string;
  position: number;
  published: boolean;
  items: ModuleItem[];
}

export interface AssignmentGroup {
  id: string;
  course_id: string;
  name: string;
  weight: number | null;
  drop_lowest_n: number;
  position: number;
}

export interface AssignmentSummary {
  id: string;
  title: string;
  points_possible: number;
  due_at: string | null;
  assignment_group_id: string | null;
  published: boolean;
}

export interface CourseDetail extends Course {
  modules: Module[];
  assignment_groups: AssignmentGroup[];
  assignments: AssignmentSummary[];
}
